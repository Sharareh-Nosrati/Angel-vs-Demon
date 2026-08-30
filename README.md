# Angel vs Demon

A conversational AI game where two competing personalities — **Sunny** (an Angel) and **Crowley** (a Demon) — respond to moral dilemmas and try to persuade the user toward their side. The app tracks the user's alignment over multiple rounds and declares a winner (Heaven or Hell) at the end.

Built for the AI Engineer Assignment at Luxia S.r.l.

---

## Features

- **Two AI personalities** (Sunny and Crowley) with distinct, consistent voices, powered by GPT-4o-mini
- **Reactive dialogue**: Crowley sees and responds to Sunny's argument, so the two feel like they're actually debating each other, not just answering independently
- **Alignment tracking**: every user response is scored from -1.0 (fully selfish) to +1.0 (fully selfless) using a consequentialist (utilitarian) framework, and the running average is converted into a Heaven % / Hell % split
- **Adaptive dilemmas**: the first 3 rounds are fixed warm-up questions; the next 3 are generated live by GPT based on the user's alignment profile so far, to probe their tendencies further
- **Structured JSON output**: the alignment analyzer uses OpenAI's Structured Outputs (JSON Schema) instead of manual text parsing, so the score/reasoning are always returned in a reliable format
- Simple Streamlit web UI: chat with both characters, see round-by-round history, and track the alignment bar live

---

## Requirements

- Python 3.9+
- An OpenAI API key with access to `gpt-4o-mini`

---

## Setup

1. **Clone or download this project folder.**

2. **Install dependencies:**
   ```bash
   pip install streamlit openai
   ```

3. **Set your OpenAI API key.**

   For local testing, the key is currently read from a variable at the top of `streamlit_app.py`. For anything beyond local testing, use an environment variable or Streamlit secrets instead (see [Production Plan](./ARCHITECTURE_AND_DESIGN.md) for details):

   ```bash
   # Option A: environment variable
   export OPENAI_API_KEY="your-key-here"       # macOS/Linux
   setx OPENAI_API_KEY "your-key-here"          # Windows (PowerShell: use $Env:)
   ```

   Then in `streamlit_app.py`, replace the hardcoded key with:
   ```python
   import os
   API_KEY = os.getenv("OPENAI_API_KEY")
   ```

---

## Running the app

```bash
python -m streamlit run streamlit_app.py
```

This starts a local web server (usually at `http://localhost:8501`) and should open automatically in your browser. If it doesn't, open that URL manually.

---

## How to play

1. Click **Start Game**.
2. Read the dilemma, and Sunny's and Crowley's arguments.
3. Type your answer in your own words — a single word, a full sentence, or an explanation of your reasoning are all fine.
4. Submit your answer. The game analyzes it, updates your Heaven/Hell alignment, and shows who won that round.
5. After 3 warm-up rounds and 3 adaptive rounds (6 total), the game ends and declares an overall winner.
6. Expand **Game History** at any point to review all your answers and their scores.

---

## Project structure

```
streamlit_app.py    # Full application: characters, alignment analyzer, game loop, UI
README.md                     # This file
ARCHITECTURE_AND_DESIGN.md    # Design choices and production plan
CHALLENGES.md                 # Challenges encountered during development (solved and open)
```

All application logic currently lives in a single file for simplicity, given the scope of this assignment. See `ARCHITECTURE_AND_DESIGN.md` for how this would be restructured for a production deployment.
