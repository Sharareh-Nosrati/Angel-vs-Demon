# Architecture & Design Choices

## Overview

The application is built around four cooperating components:

1. **Two character agents** (Sunny and Crowley) — each a GPT-4o-mini call with a distinct system prompt
2. **An alignment analyzer** — a separate GPT-4o-mini call that scores the user's response on a -1.0 to +1.0 scale, using OpenAI's Structured Outputs to guarantee a valid, parseable result
3. **A dilemma source** — 3 fixed "warm-up" dilemmas, followed by 3 dilemmas generated dynamically based on the user's alignment profile so far
4. **A Streamlit UI** — manages game state via `st.session_state` and renders the conversation, scores, and history

These are intentionally kept as separate prompts/functions rather than one combined mega-prompt, because each has a different job (persuade vs. judge vs. generate) and mixing them made behavior harder to control and debug during development.

---

## Key design decisions

### Why a separate "alignment analyzer" instead of asking Sunny/Crowley to self-report a winner?

Early on, it would have been tempting to have Sunny and Crowley each claim victory in their own reply. This was rejected because it conflates two very different jobs: *persuading* the user (which benefits from personality, exaggeration, and bias) and *judging* the user's response (which needs to be as neutral and consistent as possible). Separating them let the analyzer be tuned independently, with its own few-shot examples and scoring rules, without affecting how in-character Sunny and Crowley sound.

### Why Structured Outputs (JSON Schema) instead of parsing plain text?

The first working version of the analyzer asked the model to reply in a fixed three-line text format (`SCORE:`, `AMBIGUOUS:`, `SHORT_ANSWER:`) and parsed it with string splitting. This worked most of the time, but was fragile by construction — any deviation in formatting (extra whitespace, reordered lines, added commentary) could silently produce a wrong or default value. Switching to `response_format` with a strict JSON Schema removes this entire class of bugs: the API guarantees the output matches the schema, so parsing is just `json.loads()`.

### Why a consequentialist (utilitarian) framing for scoring?

The first version of the alignment prompt scored purely on "does this choice match a moral rule" (e.g., lying is always closer to Hell). This broke down on nuanced dilemmas — for example, lying to protect a friend scored as strongly selfish, which didn't match the intent behind the choice. Reframing the analyzer around net benefit / harm mitigation, and adding conditional answer handling ("it depends on how much harm it causes" is not treated as ambiguous, but scored based on the stated threshold), produced more human-plausible scores on nuanced cases.

### Why treat short, unhedged answers as confident rather than uncertain?

Initial testing showed that one-word answers ("Keep", "Refuse") received inconsistent scores across runs (anywhere from 0.6 to 0.9) purely due to model sampling variance, since the prompt didn't specify how confident a short answer should be treated as. The prompt was updated to explicitly state that brevity without hedging language ("maybe", "I think") signals conviction, not doubt, and should score in the 0.8–1.0 range. This made scoring far more consistent across repeated tests with the same kind of answer.

### Why log responses to a Google Sheet instead of a database?

Once the app was deployed publicly, there was no way to review what other people answered after their session ended, since all state lives in `st.session_state` and disappears on refresh. A full database (e.g. Supabase, Postgres) was considered but judged disproportionate for this assignment's scope. Instead, each completed round is sent via a simple HTTP POST to a Google Apps Script Web App bound to a Google Sheet, which appends a row (timestamp, dilemma, answer, score, reasoning, etc.). This required no new infrastructure or credentials beyond a Google account, is trivial to inspect (it's just a spreadsheet), and is wrapped in a `try/except` so that a logging failure never breaks gameplay — it fails silently and the game continues normally.

### Why fixed warm-up dilemmas + adaptive generation afterward?

Three fixed dilemmas at the start give every player the same baseline (useful for consistency and testing), covering three different moral dimensions (sacrifice, honesty/self-interest, loyalty/fairness). After that baseline exists, the game has enough signal to generate dilemmas tailored to the player's apparent tendency — either probing harder on their dominant leaning, or exploring a fresh moral dimension if they're closer to neutral. This mirrors how adaptive psychometric assessments work (start broad, then narrow based on responses) while staying lightweight, as the assignment explicitly called for "a simple scoring system."

### Why keep the ambiguous-answer retry loop instead of just defaulting to a neutral score?

If a user's answer genuinely doesn't indicate a choice (e.g., "I don't know" or an incomplete sentence), silently scoring it as neutral (0.0) would let a non-answer count as a real data point and skew the running average. Instead, the UI asks the user to clarify, which keeps the alignment score meaningful.

---

## Deployment

The app is deployed on Streamlit Community Cloud, connected to a private GitHub repository that auto-redeploys on every push. The OpenAI API key is stored using Streamlit's built-in secrets management (`st.secrets`), configured in the Cloud dashboard rather than committed to source control — `.gitignore` explicitly excludes the local `secrets.toml` file to prevent accidental leaks. This was a deliberate minimum-viable-security choice: it avoids hardcoded credentials in the repository without requiring a full secrets manager, which would be excessive for a project at this scale.

## Known limitations

- **Sunny and Crowley don't literally "evolve"** across rounds — each response is generated fresh from the same system prompt, without memory of prior rounds' dialogue. They currently only react to each other within a single round, not across the whole game. See the Production Plan below for how this could be extended.
- **Two sequential API calls per round** (Sunny, then Crowley) instead of parallel calls, because Crowley's response is written to react to Sunny's — see `CHALLENGES.md` for the tradeoff this represents.
- **Ambiguity detection and confidence calibration rely on model judgment**, not deterministic rules, so behavior — while now much more stable after prompt refinement — is not 100% guaranteed to be identical on every run.

---

## Production plan

If this were to move beyond a prototype toward a production deployment, the priorities would be:

1. **Secrets management**: ✅ already in place for this deployment via `st.secrets` / Streamlit Cloud's Secrets settings, rather than hardcoding the key in source. For a larger production system, this would move to a dedicated secrets manager (e.g. AWS Secrets Manager, HashiCorp Vault) with key rotation.
2. **Persistent storage**: currently, live game state lives in `st.session_state` and is lost on refresh; only completed rounds are persisted (to Google Sheets, see below). A production version would persist full sessions in a proper database, so a user could resume an in-progress game.
3. **Observability**: a basic version of this already exists — every completed round is logged to a Google Sheet with its score and reasoning, via a lightweight Apps Script webhook. For real production use, this should move to a proper structured logging/analytics pipeline (e.g. a hosted database or logging service) so that scoring quality and drift can be queried and monitored over time, and so the data can double as a labeled dataset for potentially fine-tuning a cheaper/faster scoring model.
4. **Cost and latency controls**: cache or reuse warm-up dilemma responses where possible, and consider a smaller/faster model for the alignment analyzer specifically, since it's a comparatively simple classification task.
5. **True character evolution**: pass a summary of prior rounds into Sunny's and Crowley's prompts so their tone can genuinely shift over a session (e.g., become more targeted or more desperate as they fall behind).
6. **Testing**: build a small regression test suite of dilemma/response pairs with expected score ranges (many of which already exist as few-shot examples in the prompt) to catch scoring drift whenever the prompt or model changes.
7. **Rate limiting and abuse protection**, since this would be a public-facing app making paid API calls on the user's behalf.
