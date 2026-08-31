# Angel vs Demon

A conversational AI game where two competing personalities — **Sunny** (an Angel) and **Crowley** (a Demon) — respond to moral dilemmas and try to persuade the user toward their side. The app tracks the user's alignment over multiple rounds and declares a winner (Heaven or Hell) at the end.

Built for the AI Engineer Assignment at Luxia S.r.l.

---

## 🔗 Quick links

| What | Link | What it's for |
|---|---|---|
| **Play the game** | [angel-vs-demon-6cdvv8yykkq9d6ddtjtzpd.streamlit.app](https://angel-vs-demon-6cdvv8yykkq9d6ddtjtzpd.streamlit.app/) | The live, deployed app. No installation needed — anyone with this link can open it in a browser and play immediately. |
| **View all recorded answers** | [Google Sheet](https://docs.google.com/spreadsheets/d/14RbU138j62o6G-8ygUnzRFsw_Cy_mPKfvjH98_Bk94E/edit?usp=sharing) | Every completed round from every player of the live app is automatically logged here in real time (timestamp, dilemma, answer, score, and the reasoning behind the score) — see [Response logging](#response-logging-explained) below for how this works. |
| **Game flow diagram** | [FLOWCHART.md](./FLOWCHART.md) | A visual step-by-step diagram of what happens during one round of the game. |

---

## Features

- **Two AI personalities** (Sunny and Crowley) with distinct, consistent voices, powered by GPT-4o-mini
- **Reactive dialogue**: Crowley sees and responds to Sunny's argument, so the two feel like they're actually debating each other, not just answering independently
- **Alignment tracking**: every user response is scored from -1.0 (fully selfish) to +1.0 (fully selfless) using a consequentialist (utilitarian) framework, and the running average is converted into a Heaven % / Hell % split
- **Adaptive dilemmas**: the first 3 rounds are fixed warm-up questions; the next 3 are generated live by GPT based on the user's alignment profile so far, to probe their tendencies further
- **Structured JSON output**: the alignment analyzer uses OpenAI's Structured Outputs (JSON Schema) instead of manual text parsing, so the score/reasoning are always returned in a reliable format
- Simple Streamlit web UI: chat with both characters, see round-by-round history, and track the alignment bar live
- **Response logging**: every completed round is sent to a Google Sheet (via a Google Apps Script Web App) with a timestamp, so answers from anyone using the live link can be reviewed later, even after their session ends

---

## Live demo

A deployed version of this app is available here:

**[https://angel-vs-demon-6cdvv8yykkq9d6ddtjtzpd.streamlit.app/](https://angel-vs-demon-6cdvv8yykkq9d6ddtjtzpd.streamlit.app/)**

Anyone with this link can play without installing anything. The source code is hosted in a private GitHub repository and deployed via Streamlit Community Cloud, which redeploys automatically whenever the repository is updated.

---

## Response logging, explained

The app itself doesn't remember anything after you close the browser tab — each visit starts a fresh session. To make it possible to review what people actually answered (for example, to check the assignment's scoring behavior after the fact), every completed round from the live app is automatically sent to this Google Sheet:

**[View recorded answers](https://docs.google.com/spreadsheets/d/14RbU138j62o6G-8ygUnzRFsw_Cy_mPKfvjH98_Bk94E/edit?usp=sharing)**

Each row records: timestamp, the dilemma shown, the player's answer, the score it received (-1.0 to +1.0), whether it was flagged as ambiguous or a short answer, and the AI's written reasoning for that score. This happens automatically in the background via a small Google Apps Script webhook — no manual export or setup is needed to see new answers appear.

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

3. **Set your OpenAI API key using Streamlit secrets.**

   Create a folder named `.streamlit` in the project root, and inside it a file called `secrets.toml` (a template is provided as `secrets.toml.example`):

   ```toml
   OPENAI_API_KEY = "your-key-here"
   ```

   `.streamlit/secrets.toml` is listed in `.gitignore` and must never be committed to GitHub — it's the local/private equivalent of the "Secrets" section used on Streamlit Community Cloud.

---

## Running the app locally

```bash
python -m streamlit run streamlit_app.py
```

This starts a local web server (usually at `http://localhost:8501`) and should open automatically in your browser. If it doesn't, open that URL manually.

---

## Deploying (Streamlit Community Cloud)

The live demo linked above was deployed as follows:

1. Push the project (`streamlit_app.py`, `requirements.txt`, `.gitignore`, `README.md`) to a GitHub repository. **Never push `secrets.toml`** — `.gitignore` prevents this by default.
2. On [share.streamlit.io](https://share.streamlit.io), sign in with GitHub and create a new app pointing at the repository, branch `main`, and main file `streamlit_app.py`.
3. Under **Advanced settings → Secrets**, add:
   ```toml
   OPENAI_API_KEY = "your-key-here"
   ```
4. Deploy. Streamlit Cloud will automatically redeploy the app on every push to the repository.

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
streamlit_app.py              # Full application: characters, alignment analyzer, game loop, UI, sheet logging
requirements.txt               # Python dependencies
.gitignore                     # Excludes secrets.toml and other local files from version control
secrets.toml.example           # Template showing the expected format for .streamlit/secrets.toml
README.md                      # This file
FLOWCHART.md                   # Visual diagram of the game's logic flow
ARCHITECTURE_AND_DESIGN.md     # Design choices and production plan
CHALLENGES.md                  # Challenges encountered during development (solved and open)
```

All application logic currently lives in a single file for simplicity, given the scope of this assignment. See `ARCHITECTURE_AND_DESIGN.md` for how this would be restructured for a production deployment.
