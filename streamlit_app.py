"""
==============================================================
Angel vs Demon — Streamlit UI (Luxia S.r.l. AI Engineer Assignment)
==============================================================
Web interface for the Angel vs Demon game.

Run with:
    python -m streamlit run streamlit_app.py
==============================================================
"""

import json
import requests
import streamlit as st
from openai import OpenAI

# URL of the Google Apps Script Web App that logs each answer to a Google Sheet.
SHEET_LOG_URL = "https://script.google.com/macros/s/AKfycbwTBwFXdvqxPmNTWRMJ_-1ZV2iK0gpR7fz4x5btKMjdvlM5hUVlvLGHKtjY64-h-CRzZg/exec"

# API key is read from Streamlit secrets (see .streamlit/secrets.toml locally,
# or the "Secrets" section in Streamlit Community Cloud when deployed).
# Never hardcode API keys in source code that gets pushed to a repository.
API_KEY = st.secrets["OPENAI_API_KEY"]

client = OpenAI(api_key=API_KEY)


# ==============================================================
# Character system prompts: Sunny (Angel) and Crowley (Demon)
# ==============================================================
sunny_system_prompt = """You are Sunny, an Angel competing for a promotion in Heaven's ranks.
You advocate for actions that bring the greatest well-being, protect others, minimize harm,
and maximize total positive impact.
You speak warm-heartedly, with optimism, and enjoy inserting quick, lighthearted dad jokes or puns.
STRICT LIMITS & RULES:
- Persuade the user to choose the option that leads to the greatest good or lowest overall
  damage for everyone involved.
- Maximum 2 short sentences.
- Never exceed 35 words total."""

crowley_system_prompt = """You are Crowley, a Demon competing for a promotion in Hell's ranks.
You advocate for pure self-preservation, immediate personal gain, laziness, and taking the
easy path regardless of the impact on others.
You speak with sharp sarcasm, dry dark humor, and a cynical edge.
STRICT LIMITS & RULES:
- Briefly mock Sunny's argument or idealism.
- Persuade the user that their own comfort, wealth, or peace of mind comes before anyone
  else's well-being.
- Maximum 2 short sentences.
- Never exceed 35 words total."""


def get_sunny_response(dilemma):
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sunny_system_prompt},
            {"role": "user", "content": dilemma}
        ]
    ).choices[0].message.content


def get_crowley_response(dilemma, sunny_reply):
    crowley_prompt = f"""The user asked: "{dilemma}"

Sunny the Angel just said: "{sunny_reply}"

Now give your response to the user, and briefly mock or counter what Sunny said."""

    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": crowley_system_prompt},
            {"role": "user", "content": crowley_prompt}
        ]
    ).choices[0].message.content


# ==============================================================
# Alignment analyzer (Structured JSON Output)
#
# Development history (kept here for the final report):
#   - v1: Neutral prompt, no examples. Had a bug where short answers
#     like "my loved one" were misjudged as Heaven, because the model
#     wasn't told to first identify which option is Heaven/Hell.
#     Fixed with chain-of-thought prompting.
#   - v2: Same logic with a "psychologist" persona. Interesting finding:
#     on a borderline dilemma (lying to protect a friend), the neutral
#     version scored it as Hell (-0.8) while the psychologist version
#     scored it as Heaven (+0.8) - showing that persona can flip the
#     model's entire moral judgment framework.
#   - v3: Reverted to a neutral prompt but added 10 few-shot examples,
#     which made borderline-case behavior more controlled and predictable.
#   - Final (this version): Reframed around a utilitarian/consequentialist
#     lens (net benefit vs. harm) with explicit handling of conditional
#     answers ("it depends on...") so they are no longer misjudged as
#     ambiguous. Switched from manual text parsing to OpenAI's Structured
#     Outputs (JSON Schema) to eliminate parsing fragility.
# ==============================================================
alignment_analyzer_prompt = """You are an advanced alignment analyzer for a moral dilemma game.
Your task is to analyze the user's response to a moral dilemma and evaluate their decision
based on overall outcome quality, harm mitigation, and net societal benefit versus purely
selfish gain.

CRITICAL INSTRUCTIONS:
1. Identify the core dilemma choices:
   - Maximizing net benefit / minimizing total harm (High Score: +0.1 to +1.0)
   - Prioritizing pure self-interest, personal profit, or avoiding minimal friction at
     others' expense (Low Score: -0.1 to -1.0)
2. Handle Conditional & Nuanced Answers:
   - Do NOT mark answers as AMBIGUOUS if the user sets a logical condition based on scale,
     impact, or severity (e.g., "depends on how much harm it causes").
   - If the condition favors minimizing major harm while accepting minor tradeoffs, assign
     a positive score. If it prioritizes self-interest unless extreme consequences occur,
     assign a negative score.
   - Mark ambiguous=true ONLY if the user explicitly declines to choose, gives complete
     nonsense, or states they cannot decide.
3. Ignore minor typos, missing letters, or incomplete words as long as the intended option
   is still clearly identifiable from context. Do not penalize the score or treat the
   response as ambiguous because of small spelling mistakes.
4. short_answer=true if the response is under ~3 words with no reasoning given.
5. Calibrate confidence correctly:
   - Short, direct answers (a single word or brief phrase with NO hedging language like
     "maybe", "I guess", "probably", "I think") should be treated as CONFIDENT decisions,
     not uncertain ones. Assign these a strong score (0.8 to 1.0 in the corresponding
     direction), since brevity without hedging indicates conviction, not doubt.
   - Reserve lower-magnitude scores (closer to 0) for responses that explicitly show
     hesitation, hedging, or mixed reasoning (e.g. "I'm not sure, but maybe...").
   - Do not lower the score just because the dilemma's wording sounds severe or the
     stakes seem high — score based on how confidently the user stated their choice,
     not how dramatic the dilemma text is.

Here are examples of how to score conditional and nuanced answers:

Example 1:
Dilemma: "You are offered a promotion that requires overseeing a project that causes environmental harm."
Response: "It depends on how much harm it causes. If it affects a lot of people or nature badly, I won't accept. If minor, I will."
score: 0.5, ambiguous: false, short_answer: false
reasoning: "The user sets a threshold based on net impact and harm mitigation rather than blindly accepting for financial gain."

Example 2:
Dilemma: "You witness a coworker stealing office supplies. Do you report them or stay silent?"
Response: "I stay silent because it's not my business."
score: -0.6, ambiguous: false, short_answer: true
reasoning: "Choosing silence avoids minor personal conflict at the expense of organizational fairness."

Example 3:
Dilemma: "You stumble upon evidence to exonerate an innocent person on death row, but it will expose a company scandal."
Response: "I'd reveal the truth to save the life, but try to find a way to help my colleagues find new jobs."
score: 0.95, ambiguous: false, short_answer: false
reasoning: "Prevents catastrophic harm (death of an innocent) while actively seeking to mitigate secondary harm to colleagues."

Example 4:
Dilemma: "You find a wallet with $1000 cash. Do you keep it or try to return it?"
Response: "If I am in desperate financial trouble I might keep it, otherwise I return it."
score: 0.2, ambiguous: false, short_answer: false
reasoning: "Balancing personal urgent survival needs against return of property, leaning toward moral action under normal conditions."

Example 5:
Dilemma: "You can either save your loved one or save 100 strangers."
Response: "100 stranger"
score: 0.9, ambiguous: false, short_answer: true
reasoning: "Short, direct choice (with a minor typo) with no hedging language, indicating a confident preference for the greater collective good."

Example 6:
Dilemma: "You can donate your bonus to charity or keep it for yourself."
Response: "I don't know, this is too hard to decide."
score: 0.0, ambiguous: true, short_answer: false
reasoning: "The user explicitly states they cannot decide, with no identifiable leaning."

Now analyze the dilemma and response the user provides."""

alignment_schema = {
    "type": "json_schema",
    "json_schema": {
        "name": "alignment_eval",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "score": {"type": "number", "description": "Score from -1.0 to +1.0"},
                "ambiguous": {"type": "boolean"},
                "short_answer": {"type": "boolean"},
                "reasoning": {"type": "string"}
            },
            "required": ["score", "ambiguous", "short_answer", "reasoning"],
            "additionalProperties": False
        }
    }
}


def analyze_alignment(dilemma, user_response):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": alignment_analyzer_prompt},
            {"role": "user", "content": f'Dilemma: "{dilemma}"\n\nUser response: "{user_response}"'}
        ],
        response_format=alignment_schema
    )
    return json.loads(response.choices[0].message.content)


# ==============================================================
# Dilemmas: fixed warm-up set + adaptive generator
# ==============================================================
WARMUP_DILEMMAS = [
    "You can either save your loved one or save 100 strangers. What do you choose?",
    "You find a wallet with $1000 cash and no ID inside except a name. Do you keep it or try to return it?",
    "You witness a coworker stealing office supplies. Do you report them or stay silent?",
]

dilemma_generator_prompt = """You are a creative writer for a moral dilemma game.
You will be given the user's current alignment profile (a percentage leaning toward
"Heaven"/selfless or "Hell"/selfish, based on their previous answers) and a short
history of the dilemmas they've already faced.

Your job is to create ONE new, original moral dilemma that:
- Is different from the dilemmas already used (avoid repeating themes)
- Is short (1-2 sentences), presented as a clear choice between two options
- Is calibrated to further probe the user's current tendency: if they lean strongly
  toward one side, make the dilemma harder/more nuanced to really test how far that
  tendency goes. If they're closer to neutral, pick a fresh moral dimension to explore.

Respond with ONLY the dilemma text, nothing else."""


def generate_adaptive_dilemma(heaven_pct, history):
    history_summary = "\n".join([f"- {h['dilemma']}" for h in history])
    user_message = f"""Current alignment: {heaven_pct}% Heaven / {100 - heaven_pct}% Hell

Dilemmas already used:
{history_summary}

Generate the next dilemma."""

    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": dilemma_generator_prompt},
            {"role": "user", "content": user_message}
        ]
    ).choices[0].message.content.strip()


# ==============================================================
# Game state management via Streamlit session_state
# ==============================================================
def get_heaven_percentage(history):
    if not history:
        return 50.0
    avg = sum(h["score"] for h in history) / len(history)
    return round(((avg + 1) / 2) * 100, 1)


def log_to_sheet(dilemma, user_answer, result):
    """
    Sends one round's data to the Google Sheet via the Apps Script Web App.
    Wrapped in try/except so that a logging failure (e.g. network issue)
    never breaks the game itself.
    """
    payload = {
        "dilemma": dilemma,
        "user_answer": user_answer,
        "score": result["score"],
        "ambiguous": result["ambiguous"],
        "short_answer": result["short_answer"],
        "reasoning": result["reasoning"],
    }
    try:
        requests.post(SHEET_LOG_URL, json=payload, timeout=5)
    except requests.RequestException:
        pass  # Logging is best-effort; don't interrupt gameplay on failure.


def init_session():
    if "history" not in st.session_state:
        st.session_state.history = []
    if "round_number" not in st.session_state:
        st.session_state.round_number = 0
    if "current_dilemma" not in st.session_state:
        st.session_state.current_dilemma = None
    if "current_sunny" not in st.session_state:
        st.session_state.current_sunny = None
    if "current_crowley" not in st.session_state:
        st.session_state.current_crowley = None
    if "waiting_for_answer" not in st.session_state:
        st.session_state.waiting_for_answer = False
    if "last_round_result" not in st.session_state:
        st.session_state.last_round_result = None
    if "game_over" not in st.session_state:
        st.session_state.game_over = False


TOTAL_ROUNDS = 6  # 3 warm-up + 3 adaptive


def start_new_round():
    """Picks the next dilemma and gets Sunny's and Crowley's responses."""
    idx = st.session_state.round_number  # 0-indexed

    if idx < len(WARMUP_DILEMMAS):
        dilemma = WARMUP_DILEMMAS[idx]
    else:
        heaven_pct = get_heaven_percentage(st.session_state.history)
        dilemma = generate_adaptive_dilemma(heaven_pct, st.session_state.history)

    with st.spinner("Sunny and Crowley are thinking..."):
        sunny_reply = get_sunny_response(dilemma)
        crowley_reply = get_crowley_response(dilemma, sunny_reply)

    st.session_state.current_dilemma = dilemma
    st.session_state.current_sunny = sunny_reply
    st.session_state.current_crowley = crowley_reply
    st.session_state.waiting_for_answer = True
    st.session_state.last_round_result = None


def submit_answer(user_response):
    """Analyzes the user's answer and updates the alignment score."""
    with st.spinner("Analyzing your answer..."):
        result = analyze_alignment(st.session_state.current_dilemma, user_response)

    if result["ambiguous"]:
        # Instead of a terminal-style while-loop, we simply show a warning
        # and let the user retype in the same input box.
        st.session_state.last_round_result = {"ambiguous_warning": True}
        return

    st.session_state.history.append({
        "dilemma": st.session_state.current_dilemma,
        "user_response": user_response,
        "score": result["score"],
        "short_answer": result["short_answer"],
        "reasoning": result["reasoning"],
    })
    log_to_sheet(st.session_state.current_dilemma, user_response, result)
    st.session_state.round_number += 1
    st.session_state.waiting_for_answer = False
    st.session_state.last_round_result = result

    if st.session_state.round_number >= TOTAL_ROUNDS:
        st.session_state.game_over = True


# ==============================================================
# UI
# ==============================================================
st.set_page_config(page_title="Angel vs Demon", page_icon="⚖️", layout="centered")
init_session()

st.title("⚖️ Angel vs Demon")
st.caption("Sunny and Crowley are competing for a promotion — and you're the one who decides who wins.")

st.info(
    "💡 **Tip:** Answer however feels natural to you — a single word, a full sentence, "
    "or even an explanation of your reasoning. There's no fixed format, so feel free to "
    "just write what you're thinking."
)

# Alignment bar - always shown at the top of the page
heaven_pct = get_heaven_percentage(st.session_state.history)
col1, col2 = st.columns(2)
with col1:
    st.metric("😇 Heaven", f"{heaven_pct}%")
with col2:
    st.metric("😈 Hell", f"{100 - heaven_pct}%")
st.progress(heaven_pct / 100)

st.divider()

# ---------------------------------------------------------------
# State 1: game hasn't started yet
# ---------------------------------------------------------------
if st.session_state.round_number == 0 and not st.session_state.waiting_for_answer:
    st.write("Ready to enter the competition? A few dilemmas are waiting for you...")
    if st.button("🎮 Start Game", type="primary"):
        start_new_round()
        st.rerun()

# ---------------------------------------------------------------
# State 2: game is over
# ---------------------------------------------------------------
elif st.session_state.game_over:
    winner = "Sunny (Heaven) 😇" if heaven_pct > 50 else ("Crowley (Hell) 😈" if heaven_pct < 50 else "Tie 🤝")
    st.success(f"🏁 Game over! Winner: **{winner}**")
    st.write(f"Final alignment: {heaven_pct}% Heaven / {100 - heaven_pct}% Hell")

    if st.button("🔄 New Game"):
        for key in ["history", "round_number", "current_dilemma", "current_sunny",
                    "current_crowley", "waiting_for_answer", "last_round_result", "game_over"]:
            del st.session_state[key]
        st.rerun()

# ---------------------------------------------------------------
# State 3: waiting for the user's answer to the current round
# ---------------------------------------------------------------
elif st.session_state.waiting_for_answer:
    st.subheader(f"Round {st.session_state.round_number + 1} of {TOTAL_ROUNDS}")
    st.info(f"🎭 **Dilemma:** {st.session_state.current_dilemma}")

    st.markdown(f"😇 **Sunny:** {st.session_state.current_sunny}")
    st.markdown(f"😈 **Crowley:** {st.session_state.current_crowley}")

    if st.session_state.last_round_result and st.session_state.last_round_result.get("ambiguous_warning"):
        st.warning("⚠️ I couldn't quite tell which option you're leaning toward. Could you say it more clearly?")

    user_response = st.text_input("💬 What's your take?", key=f"answer_{st.session_state.round_number}")
    if st.button("Submit Answer", type="primary"):
        if user_response.strip():
            submit_answer(user_response)
            st.rerun()
        else:
            st.warning("Please write an answer first.")

# ---------------------------------------------------------------
# State 4: between rounds - show the previous round's result and a "next" button
# ---------------------------------------------------------------
else:
    last = st.session_state.history[-1]
    round_winner = "Sunny (Heaven) 😇" if last["score"] > 0 else ("Crowley (Hell) 😈" if last["score"] < 0 else "Tie 🤝")
    st.success(f"Round {st.session_state.round_number} result: **{round_winner}** wins (score: {last['score']})")
    st.caption(last["reasoning"])

    if st.button("➡️ Next Round", type="primary"):
        start_new_round()
        st.rerun()

# ---------------------------------------------------------------
# Full conversation history (collapsible)
# ---------------------------------------------------------------
if st.session_state.history:
    with st.expander(f"📜 Game History ({len(st.session_state.history)} rounds)"):
        for i, h in enumerate(st.session_state.history, start=1):
            st.markdown(f"**Round {i}:** {h['dilemma']}")
            st.markdown(f"> Your answer: _{h['user_response']}_")
            st.markdown(f"> Score: `{h['score']}` — {h['reasoning']}")
            st.divider()
