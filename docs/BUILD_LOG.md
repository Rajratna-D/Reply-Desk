# Build log

Purpose: raw material for the DEV post. Record decisions, bugs, fixes, and real measurements as they happen. Add one dated line at a time. Do not write down numbers that were not measured. The agent and the developer both append here.

Format: `YYYY-MM-DD HH:MM IST - [type] note` where type is one of `decision`, `bug`, `fix`, `measurement`, `user`, `note`.

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

- 2026-10-14 - [decision] Chose to build ReplyDesk: a configurable customer-reply assistant for small sellers (English, Hindi, Marathi, Hinglish). Local model via Ollama, SQLite storage, Streamlit UI.
- 2026-10-14 - [decision] Scope kept small: draft-only, no integrations, no accounts. Seller always reviews.
- 2026-10-14 - [note] Docs, schema, three fictional sample shops, and 25 eval questions drafted before coding. Repo created on 2026-10-14 (inside the challenge window which started 2026-10-12).
- 2026-10-14 09:55 IST - [decision] Added simulated customer chat and owner inbox pages for side-by-side demo. reply_log acts as the message queue (seller_action IS NULL for pending review). Verified that no database schema change is needed.
- 2026-10-14 10:05 IST - [measurement] Milestone 1 completed. 18 pytest unit tests passed (including live smoke test on local Ollama server). Verified draft_reply across Urban Thread (8.3s), Sweet Crumbs (7.7s), and Kalakruti Jewels (7.2s). Verified needs_check correctly triggers on custom work.
- 2026-10-14 10:18 IST - [measurement] Verified gemma2:2b on RTX 3050 Laptop 6 GB. ollama ps: 1.9 GB size, 100% GPU offload, NUM_CTX=4096. Token generation speed: 68.7 tokens/sec. Latency per draft: Sweet Crumbs (3.6s), Kalakruti Jewels (3.5s). All 18 pytest tests pass in 6.77s.
- 2026-10-14 10:35 IST - [note] Milestone 2 completed. Streamlit UI with Customer Chat simulator, Owner Inbox queue, manual Reply scratchpad, Setup & catalogue editor (form & CSV), History audit, and Settings built and running on localhost:8501.
- 2026-10-14 11:05 IST - [fix] Complete UI overhaul to eliminate Streamlit prototype aesthetics and 'AI slop'. Added .streamlit/config.toml (dark base, emerald #10b981 primary, minimal toolbar). Fixed Streamlit React DOM unclosed markdown div bug. Converted sidebar radio buttons to Linear-style menu items. Styled customer chat simulator with WhatsApp-like messenger frame, green chat bubbles, and internal scroll container. Refined inbox triage cards, high-contrast editable textareas, and telemetry widgets. All 18 pytest tests pass.
- 2026-10-14 12:34 IST - [measurement] Dev split eval run on gemma2:2b (12 cases). Built eval/run_eval.py and Streamlit eval dashboard. Results: Overall pass rate 75.0% (9/12), facts_ok 11/12 (91.7%), needs_check_ok 11/12 (91.7%), language_ok 11/12 (91.7%), median latency 3438 ms.
- 2026-10-14 13:10 IST - [measurement] Full 25-case benchmark run on gemma2:2b. Results: Overall pass rate 68.0% (17/25), facts_ok 25/25 (100.0% with substring matching), needs_check_ok 20/25 (80.0%), language_ok 22/25 (88.0%), median latency 3496 ms. English 10/13, Hinglish 5/6, Marathi 1/3, Hindi 1/3.
- 2026-10-14 19:36 IST - [measurement] Re-ran 25-case benchmark on gemma2:2b after fixing SC-16 digit-boundary scoring bug in eval/run_eval.py. Results: Overall pass rate 68.0% (17/25), facts_ok 23/25 (92.0%), needs_check_ok 22/25 (88.0%), language_ok 22/25 (88.0%), median latency 3395 ms. SC-16 correctly fails for omitting the Rs 50 delivery fee.
- 2026-10-14 20:44 IST - [measurement] Full 25-case benchmark run on gemma2:9b (next size up). ollama ps: 7.1 GB size, 46%/54% CPU/GPU offload on 6 GB RTX 3050 Laptop. Results: Overall pass rate 72.0% (18/25), facts_ok 23/25 (92.0%), needs_check_ok 25/25 (100.0%), language_ok 20/25 (80.0%), median latency 12395 ms. English 12/13 (92.3%), Hinglish 5/6 (83.3%), Marathi 1/3 (33.3%), Hindi 0/3 (0.0%). 100% correct needs_check flags (cleanly handles KJ-25 prompt injection and SC-14 gluten uncertainty), but tends to translate Hindi/Marathi inquiries into English replies without explicit script anchoring.


