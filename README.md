# Angel vs Demon

A terminal-based moral-alignment game built for an AI Engineer take-home assignment (Luxia S.r.l.). Two GPT-4o-mini personas — Sunny (an angel arguing from a utilitarian, greatest-good standpoint) and Crowley (a demon arguing from pure self-interest) — respond to a moral dilemma and try to win the player over. The player's own answer is then scored by a third "alignment analyzer" model call, and their cumulative leaning toward Heaven or Hell is tracked across a warm-up round of fixed dilemmas followed by several rounds of dilemmas generated adaptively based on how the player has been leaning so far.

## Design notes

- **Structured JSON output** (`response_format` with a strict JSON schema) is used for the alignment analyzer instead of parsing free text, so the score/ambiguous/short_answer fields are always well-formed.
- **Utilitarian framing in the scoring prompt**, with worked examples, so conditional answers ("depends how much harm it causes") are scored on their actual harm/benefit trade-off instead of being marked ambiguous by default.
- **Bounded re-prompt loop**: if the analyzer still can't extract a clear choice after a few clarification attempts, the round is scored neutral (0.0) instead of looping forever.
- Crowley's reply is generated *after* Sunny's and explicitly reacts to it, so the two calls are sequential by design (not parallelized) — Crowley needs to see what Sunny said before he can mock it.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then put your real OpenAI key in .env
python angel_vs_demon.py
```
