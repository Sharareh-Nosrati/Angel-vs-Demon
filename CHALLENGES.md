# Challenges

This document lists the concrete challenges encountered while building the alignment scoring system and the game loop, split into ones that were resolved and ones that remain open.

---

## Solved challenges

### 1. Short answers were misjudged because the model wasn't told which option was "Heaven" or "Hell"

**Problem:** The first version of the alignment analyzer asked the model directly for a score without first identifying which dilemma option represented the selfless choice and which represented the selfish one. On a short answer like `"my loved one"` (which should be the *selfish* choice, since it means letting 100 strangers die), the model incorrectly scored it as strongly *selfless* (+0.8).

**Fix:** Restructured the prompt using chain-of-thought: the model is now instructed to explicitly state which option is Heaven and which is Hell *before* judging the user's response. This resolved the misclassification immediately and consistently across repeated tests.

### 2. Persona framing could flip the model's moral judgment entirely

**Finding:** While experimenting with a "psychologist" persona for the analyzer (to better capture underlying motivation), the same borderline dilemma ("lie to protect a friend, or tell the truth and get them in trouble") produced opposite scores depending on the system prompt: a neutral/rule-based framing scored the "lie" response as strongly selfish (-0.8 to -0.9), while the psychologist framing — which was told to weigh motivation — scored the exact same response as strongly selfless (+0.8 to +1.0).

**Resolution:** This wasn't really a bug to "fix" so much as a finding to design around: persona alone can change which ethical framework the model implicitly applies (rule-based vs. motivation-based), even with identical input. The final analyzer stays with a neutral, explicitly consequentialist framing (net benefit/harm) rather than a persona-driven one, so the scoring logic is at least consistent and documented, even though it's still one particular ethical lens among several defensible ones.

### 3. Text-based output parsing was fragile

**Problem:** Early versions had the model reply in a fixed multi-line text format (`SCORE:`, `AMBIGUOUS:`, `SHORT_ANSWER:`) and extracted values with string splitting. This is inherently brittle — any formatting drift from the model (extra whitespace, reordering, added commentary) could silently break extraction or produce wrong values.

**Fix:** Switched to OpenAI's Structured Outputs with a strict JSON Schema (`response_format`), which guarantees the response always matches the expected shape. Parsing is now a simple `json.loads()` call with no manual text handling.

### 4. Conditional/nuanced answers were incorrectly flagged as ambiguous

**Problem:** Responses like `"It depends on how much harm it causes"` were marked `ambiguous=true`, forcing the user to re-answer even though the response contained a clear, reasonable, conditional stance. This added unnecessary latency, extra API cost, and hurt the flow of the game.

**Fix:** Added explicit instructions and few-shot examples showing how to score conditional answers based on their stated threshold (e.g., "accepts harm only if minor" → mildly positive) rather than treating any hedge or condition as a non-answer. `ambiguous=true` is now reserved for cases where the user genuinely gives no identifiable choice (e.g., "I don't know", an incomplete sentence, or off-topic text).

### 5. Minor typos occasionally still caused misreads

**Problem:** Even after adding an instruction to ignore minor typos, one heavily garbled word (`"appologi"`) caused a response ("I will say apology" — meaning the user chose to confront their friend) to be scored in the wrong direction.

**Status:** Largely mitigated by the typo-tolerance instruction added to the prompt, and confirmed working correctly on lighter typos (e.g., "100 strange" instead of "100 strangers", "wotuld" instead of "would") across multiple test runs. Left as a documented residual risk for very garbled input — see Open Challenges below.

### 6. Inconsistent scoring for short, unhedged answers

**Problem:** One-word answers with no reasoning ("Keep", "Refuse", "Stay silent") received noticeably inconsistent scores across repeated tests — anywhere from 0.6 to 0.9 in magnitude — because the prompt never specified how confident a short, unhedged answer should be treated as.

**Fix:** Added an explicit calibration rule: short answers with no hedging language ("maybe", "I think", "probably") should be treated as *confident* decisions and scored strongly (0.8–1.0), while lower-magnitude scores are reserved for answers that explicitly show hesitation. This made scoring visibly more stable across repeated tests with similar answers.

### 7. Double-submission from repeated button clicks

**Problem:** Testing on the deployed app showed the same round occasionally logged twice, a few seconds apart, with identical answers — from a user double-clicking "Submit Answer" (e.g. out of impatience while waiting for a response). Since Streamlit reruns the whole script on each interaction, a second click before the UI visibly updated could trigger a second, duplicate `submit_answer()` call, double-counting that round in both the alignment average and the Google Sheet log.

**Fix:** Added a `last_submitted_round` guard in session state: a round's answer is only processed once, even if the submit action fires more than once for the same round.

### 8. Long answers overflowed the input box

**Problem:** The original single-line `st.text_input` box didn't grow with longer answers — typed text would scroll out of view horizontally, making it hard for the user to review what they'd written before submitting.

**Fix:** Switched to `st.text_area` with a fixed visible height, which wraps text onto multiple lines and keeps the full answer visible while typing.

---

## Open / unsolved challenges

### 1. Heavily garbled typos can still cause misreads

As noted above, one severely garbled word was enough to flip a score's direction, even with the typo-tolerance instruction in place. A more robust fix (e.g., a lightweight spell-check pass before scoring, or requiring a minimum response length before accepting very short answers) was considered but not implemented, to keep the scoring pipeline simple as scoped for this assignment.

### 2. Sunny and Crowley don't truly "evolve" across the game

The assignment's bonus section asks for personality evolution over the course of the game. Currently, each character's response is generated independently per round from a static system prompt; there's no memory of earlier rounds carried into later ones (beyond Crowley reacting to Sunny within the *same* round). Real evolution — e.g., a character escalating its tactics as it falls behind — would require passing conversation history into the character prompts, which was left out to keep scope manageable within the assignment's time estimate.

### 3. Ethical framing is one defensible choice among several

The alignment analyzer commits to a consequentialist framing (net benefit vs. harm) after testing showed this behaved more predictably than a purely rule-based or persona-driven approach. This is a design decision, not a solved problem — a rule-based (deontological) framing would score some dilemmas differently and arguably just as validly. This tradeoff is documented rather than resolved, since moral dilemmas by nature don't have a single "correct" scoring framework.

### 4. Sequential rather than parallel character calls

Because Crowley's response is written to directly react to Sunny's, the two API calls are inherently sequential (Sunny must finish before Crowley starts), not parallel. This roughly doubles response latency compared to a fully parallel design, in exchange for the two characters feeling like they're actually debating each other rather than answering independently. This tradeoff was made deliberately in favor of dialogue quality, but is worth revisiting if latency becomes a priority.

### 5. The model sometimes conflates reasoning quality with action direction

**Problem:** Found during broader testing (including non-English input, see below): a user declined an unethical offer (taking credit for a group project they barely contributed to) — the *action itself* was the ethical, Heaven-aligned choice. But because their stated reason was mild ("it wouldn't sit right with me, though I wouldn't mind if someone else took it"), the analyzer scored it as -0.5 (Hell), effectively penalizing a genuinely good decision for having an imperfect justification.

**Status:** Open. The current prompt scores based on the combination of the action and the strength/purity of the reasoning behind it, which works well most of the time but can invert the sign of the score entirely in cases like this one, where a weak or self-focused justification accompanies an objectively selfless action. A more robust design would likely need to score the *action's direction* (Heaven vs. Hell) somewhat independently from the *conviction* behind it (which should affect magnitude, not sign) — this separation wasn't implemented within this assignment's scope.

---

## Additional testing note: multilingual input

During testing, several answers were submitted in Persian instead of English (e.g. `"من نجات یکی که دوستش دارم رو به صورت کلی انتخاب می‌کنم"`). The alignment analyzer handled these correctly without any special handling required — GPT-4o-mini is inherently multilingual, so no separate translation step was needed. This wasn't a deliberate design goal for this assignment, but it's a useful property worth highlighting: the game works for non-English speakers out of the box, and the UI hint was updated to make this explicit to players.
