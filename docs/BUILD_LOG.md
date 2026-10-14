# Build log

Purpose: raw material for the DEV post. Record decisions, bugs, fixes, and real measurements as they happen. Add one dated line at a time. Do not write down numbers that were not measured. The agent and the developer both append here.

Format: `YYYY-MM-DD HH:MM IST — [type] note` where type is one of `decision`, `bug`, `fix`, `measurement`, `user`, `note`.

## Facts to capture for the write-up

- Hardware: i5 12th gen, RTX 3050 6 GB (RAM: ___)
- Model tags tested: ___
- GPU vs CPU split per model (`ollama ps`): ___
- Median latency per reply per model: ___
- Eval results per model (facts / language / needs-check): ___
- Offline test result: ___
- Cost per reply estimate and its assumptions: ___
- First user: who, what they said, would they pay, what they asked for next: ___

## Log

- 2026-10-14 — [decision] Chose to build ReplyDesk: a configurable customer-reply assistant for small sellers (English, Hindi, Marathi, Hinglish). Local model via Ollama, SQLite storage, Streamlit UI.
- 2026-10-14 — [decision] Scope kept small: draft-only, no integrations, no accounts. Seller always reviews.
- 2026-10-14 — [note] Docs, schema, three fictional sample shops, and 25 eval questions drafted before coding. Repo created on 2026-10-14 (inside the challenge window which started 2026-10-12).
