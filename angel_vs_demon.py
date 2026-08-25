"""
==============================================================
Angel vs Demon — AI Engineer Assignment (Luxia S.r.l.)
==============================================================
نسخه‌ی ارتقایافته با:
  - Structured JSON Output (به‌جای پارس متنی شکننده)
  - پرامپت تحلیل‌گر با رویکرد پیامدگرا (Utilitarian) - پاسخ‌های
    مشروط دیگه اشتباهی AMBIGUOUS نمیشن
  - پرامپت‌های دقیق‌تر Sunny و Crowley
==============================================================
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# کلید از متغیر محیطی خونده می‌شه — قبل از اجرا یک فایل .env بساز با:
#   OPENAI_API_KEY=sk-...
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_CLARIFICATION_ATTEMPTS = 3


# ==============================================================
# ۱. شخصیت‌ها: Sunny (فرشته) و Crowley (شیطان)
# نسخه‌ی به‌روزرسانی‌شده: تمرکز روی پیامدگرایی (utilitarian framing)
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


def get_both_responses(dilemma):
    """
    Crowley's reply depends on what Sunny said (he mocks/counters it), so the two
    calls are inherently sequential — Crowley cannot be requested until Sunny's
    reply exists. True parallelism would only be possible if Crowley's prompt were
    changed to not reference Sunny's answer.
    """
    sunny_reply = get_sunny_response(dilemma)
    crowley_reply = get_crowley_response(dilemma, sunny_reply)
    return sunny_reply, crowley_reply


# ==============================================================
# ۲. تحلیل‌گر گرایش - نسخه‌ی نهایی با Structured JSON Output
# رویکرد پیامدگرا (Utilitarian): پاسخ‌های مشروط ("بستگی داره...")
# دیگه AMBIGUOUS نمیشن، بلکه بر اساس تعادل منفعت/ضرر امتیاز می‌گیرن.
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
score: 0.8, ambiguous: false, short_answer: true
reasoning: "Short but clearly identifiable choice (with a minor typo) favoring the greater collective good."

Example 6:
Dilemma: "You can donate your bonus to charity or keep it for yourself."
Response: "I don't know, this is too hard to decide."
score: 0.0, ambiguous: true, short_answer: false
reasoning: "The user explicitly states they cannot decide, with no identifiable leaning."

Now analyze the dilemma and response the user provides."""


# Schema برای تضمین اینکه خروجی همیشه یه JSON معتبر با فیلدهای درست باشه
alignment_schema = {
    "type": "json_schema",
    "json_schema": {
        "name": "alignment_eval",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "score": {
                    "type": "number",
                    "description": "Score from -1.0 (purely self-serving) to +1.0 (maximum net outcome/harm reduction)"
                },
                "ambiguous": {
                    "type": "boolean",
                    "description": "True only if user provides no decision or complete nonsense"
                },
                "short_answer": {
                    "type": "boolean",
                    "description": "True if response is under 3 words without rationale"
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of how the answer impacts overall utility"
                }
            },
            "required": ["score", "ambiguous", "short_answer", "reasoning"],
            "additionalProperties": False
        }
    }
}


def analyze_alignment(dilemma, user_response, verbose=True):
    """
    تحلیل‌گر نهایی گرایش - با خروجی ساختاریافته‌ی JSON (بدون نیاز به پارس متنی).
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": alignment_analyzer_prompt},
            {"role": "user", "content": f'Dilemma: "{dilemma}"\n\nUser response: "{user_response}"'}
        ],
        response_format=alignment_schema
    )

    result = json.loads(response.choices[0].message.content)

    if verbose:
        print(f"--- تحلیل: {result['reasoning']} ---")
        print(f"SCORE: {result['score']} | AMBIGUOUS: {result['ambiguous']} | SHORT_ANSWER: {result['short_answer']}")

    return result


def get_valid_alignment(dilemma, user_response):
    """
    اگه جواب واقعاً مبهم بود (نه مشروط)، دوباره از کاربر می‌خواد جواب واضح بده —
    حداکثر تا MAX_CLARIFICATION_ATTEMPTS بار، تا اگه کاربر مدام مبهم جواب داد
    بازی توی حلقه‌ی بی‌نهایت گیر نکنه؛ بعد از اون با امتیاز خنثی (0.0) ادامه می‌ده.
    """
    result = analyze_alignment(dilemma, user_response)
    attempts = 0

    while result["ambiguous"] and attempts < MAX_CLARIFICATION_ATTEMPTS:
        print("\n⚠️ متوجه انتخاب مشخصی از جواب شما نشدم.")
        user_response = input("لطفاً مشخص کن کدوم گزینه رو انتخاب می‌کنی: ")
        result = analyze_alignment(dilemma, user_response)
        attempts += 1

    if result["ambiguous"]:
        print("\n⚠️ همچنان انتخاب مشخصی برداشت نشد — این دور با امتیاز خنثی (0.0) ثبت می‌شه.")
        result["score"] = 0.0

    return result


# ==============================================================
# ۳. کلاس GameState - نگه‌داری امتیاز تجمعی در طول بازی
# ==============================================================
class GameState:
    def __init__(self):
        self.total_score = 0.0
        self.num_rounds = 0
        self.history = []

    def add_round(self, dilemma, user_response, result):
        self.total_score += result["score"]
        self.num_rounds += 1
        self.history.append({
            "dilemma": dilemma,
            "user_response": user_response,
            "score": result["score"],
            "short_answer": result["short_answer"],
            "reasoning": result["reasoning"],
        })

    def get_average(self):
        if self.num_rounds == 0:
            return 0.0
        return self.total_score / self.num_rounds

    def get_heaven_percentage(self):
        avg = self.get_average()
        return round(((avg + 1) / 2) * 100, 1)

    def get_current_winner(self):
        pct = self.get_heaven_percentage()
        if pct > 50:
            return "Sunny (Heaven)"
        elif pct < 50:
            return "Crowley (Hell)"
        else:
            return "Tie"

    def summary(self):
        pct = self.get_heaven_percentage()
        print(f"\n📊 دور {self.num_rounds} | گرایش: {pct}% Heaven / {100 - pct}% Hell")
        print(f"🏆 در حال حاضر جلوئه: {self.get_current_winner()}")


# ==============================================================
# ۴. دیلماهای Warm-up + تولید دیلمای تطبیقی (Adaptive)
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
  tendency goes. If they're closer to neutral, pick a fresh moral dimension to explore
  (e.g. honesty, loyalty, sacrifice, fairness, harm).

Respond with ONLY the dilemma text, nothing else. No preamble, no explanation."""


def generate_adaptive_dilemma(game_state):
    history_summary = "\n".join([f"- {h['dilemma']}" for h in game_state.history])
    heaven_pct = game_state.get_heaven_percentage()

    user_message = f"""Current alignment: {heaven_pct}% Heaven / {100 - heaven_pct}% Hell

Dilemmas already used:
{history_summary}

Generate the next dilemma."""

    new_dilemma = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": dilemma_generator_prompt},
            {"role": "user", "content": user_message}
        ]
    ).choices[0].message.content.strip()

    return new_dilemma


# ==============================================================
# ۵. حلقه‌ی اصلی بازی (Main Game Loop)
# ==============================================================
def play_round(dilemma, game_state, round_number):
    """یه دور کامل بازی: نمایش دیلما، جواب Sunny و Crowley، گرفتن جواب کاربر، تحلیل، آپدیت امتیاز."""
    print(f"\n{'=' * 60}")
    print(f"دور {round_number}")
    print(f"{'=' * 60}")
    print(f"\n🎭 دیلما: {dilemma}\n")

    sunny_reply, crowley_reply = get_both_responses(dilemma)
    print(f"😇 SUNNY: {sunny_reply}\n")
    print(f"😈 CROWLEY: {crowley_reply}\n")

    print("\n" + "👇" * 20)
    print("💬 نظر تو چیه؟ کدوم گزینه رو انتخاب می‌کنی؟")
    print("👇" * 20 + "\n")

    user_response = input(">>> ")

    result = get_valid_alignment(dilemma, user_response)
    game_state.add_round(dilemma, user_response, result)

    round_winner = (
        "Sunny (Heaven)" if result["score"] > 0
        else ("Crowley (Hell)" if result["score"] < 0 else "Tie")
    )
    print(f"\n🏆 برنده‌ی این دور: {round_winner} (امتیاز: {result['score']})")

    game_state.summary()

    return result


def run_game(num_adaptive_rounds=3):
    """
    اجرای کامل بازی:
    - ۳ دور warm-up با دیلماهای ثابت (برای شناخت اولیه از کاربر)
    - چند دور adaptive که دیلماهاشون بر اساس پروفایل کاربر تولید میشه
    """
    game_state = GameState()

    print("🎮 به بازی Angel vs Demon خوش اومدی!\n")
    print("مرحله‌ی اول: چند تا سوال پایه برای شناخت اولیه از تو...\n")

    for i, dilemma in enumerate(WARMUP_DILEMMAS, start=1):
        play_round(dilemma, game_state, round_number=i)

    print("\n\n🔮 حالا Sunny و Crowley دارن بر اساس شناختی که از تو پیدا کردن، سوالات هدفمندتری می‌سازن...\n")

    for i in range(num_adaptive_rounds):
        round_number = len(WARMUP_DILEMMAS) + i + 1
        new_dilemma = generate_adaptive_dilemma(game_state)
        play_round(new_dilemma, game_state, round_number=round_number)

    print(f"\n\n{'=' * 60}")
    print("🏁 بازی تموم شد!")
    print(f"{'=' * 60}")
    game_state.summary()

    return game_state


# ==============================================================
# اجرای بازی (وقتی این فایل مستقیم اجرا بشه)
# ==============================================================
if __name__ == "__main__":
    final_state = run_game(num_adaptive_rounds=3)
