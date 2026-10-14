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
- 2026-10-14 09:55 IST — [decision] Added simulated customer chat and owner inbox pages for side-by-side demo. reply_log acts as the message queue (seller_action IS NULL for pending review). Verified that no database schema change is needed.
- 2026-10-14 10:05 IST — [measurement] Milestone 1 completed. 18 pytest unit tests passed (including live smoke test on local Ollama server). Verified draft_reply across Urban Thread (8.3s), Sweet Crumbs (7.7s), and Kalakruti Jewels (7.2s). Verified needs_check correctly triggers on custom work.
