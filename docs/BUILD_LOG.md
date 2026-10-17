# Build log

Purpose: raw material for the DEV post. Record decisions, bugs, fixes, and real measurements as they happen. Add one dated line at a time. Do not write down numbers that were not measured. The agent and the developer both append here.

Format: `YYYY-MM-DD HH:MM IST - [type] note` where type is one of `decision`, `bug`, `fix`, `measurement`, `user`, `note`.

## Facts to capture for the write-up

- Hardware: Intel Core i5 12th gen, NVIDIA RTX 3050 Laptop GPU 6 GB (RAM: 16 GB DDR4)
- Model tags tested: gemma2:2b (1.6 GB), gemma2:9b (5.4 GB), gemma:7b (5.0 GB), gemma4:e2b (4.6 GB Q4_K_M)
- GPU vs CPU split per model (`ollama ps`):
  - gemma2:2b: 100% GPU offload (1.9 GB in VRAM)
  - gemma2:9b: 54% GPU / 46% CPU (7.1 GB total footprint, partial offload)
  - gemma:7b: 54% GPU / 46% CPU (7.8 GB total footprint, partial offload)
  - gemma4:e2b: 100% GPU offload (4.6 GB in VRAM)
- Median latency per reply per model:
  - gemma2:2b: 3440 ms (~3.4s)
  - gemma2:9b: 12395 ms (~12.4s)
  - gemma:7b: 11767 ms (~11.8s)
  - gemma4:e2b: 6389 ms (~6.4s)
- Eval results per model (facts / language / needs-check / overall pass):
  - gemma2:2b (34 cases): facts 94.1% (32/34), language 97.1% (33/34), needs-check 88.2% (30/34), overall pass 85.3% (29/34)
  - gemma2:9b (25 cases): facts 92.0% (23/25), language 80.0% (20/25), needs-check 100.0% (25/25), overall pass 72.0% (18/25)
  - gemma:7b (25 cases): facts 76.0% (19/25), language 68.0% (17/25), needs-check 80.0% (20/25), overall pass 52.0% (13/25)
  - gemma4:e2b (34 cases): facts 97.1% (33/34), language 97.1% (33/34), needs-check 100.0% (34/34), overall pass 94.1% (32/34)
- Offline test result: 100% passed (Wi-Fi disconnected, zero external network requests, pure localhost:11434 inference, tests/test_offline_integrity.py passed)
- Cost per reply estimate and its assumptions: $0.00 / reply (runs 100% on merchant's local machine, 0 cloud tokens, 0 subscription fees)
- First user: who, what they said, would they pay, what they asked for next: Tested across 3 sample boutique merchants (Urban Thread, Sweet Crumbs, Kalakruti Jewels) with multilingual inquiries in English, Hindi, Marathi, and Hinglish.

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
- 2026-10-14 21:35 IST - [measurement] Full 25-case benchmark run on gemma:7b. ollama ps: 7.8 GB size, 46%/54% CPU/GPU offload on 6 GB RTX 3050 Laptop. Results: Overall pass rate 52.0% (13/25), facts_ok 19/25 (76.0%), needs_check_ok 20/25 (80.0%), language_ok 17/25 (68.0%), median latency 11767 ms. English 7/13 (53.8%), Hindi 3/3 (100.0%), Marathi 1/3 (33.3%), Hinglish 2/6 (33.3%). Gemma 1 7B maintained Devanagari script for Hindi, but had lower factual precision and adherence than Gemma 2.
- 2026-10-14 21:41 IST - [measurement] Devanagari prompt tuning on 21 dev cases (added 9 new Hindi/Marathi cases). gemma2:2b Run 1: 95.2% (20/21), facts 21/21, check 20/21, median latency 3418 ms (Hindi 5/6, Marathi 6/6, English 5/5, Hinglish 4/4). Run 2: 95.2% (20/21), facts 21/21, check 20/21, median latency 3355 ms. Zero noise observed.
- 2026-10-14 21:47 IST - [measurement] Devanagari prompt tuning on 21 dev cases on gemma:7b. Run 1: 61.9% (13/21), facts 16/21, check 18/21, median latency 10448 ms. Run 2: 61.9% (13/21), facts 17/21, check 18/21, median latency 9382 ms.
- 2026-10-14 22:12 IST - [measurement] Complete 34-case final benchmark on gemma2:2b (dev: 21 cases, test: 13 cases). Overall pass rate 85.3% (29/34), facts_ok 32/34 (94.1%), needs_check_ok 30/34 (88.2%), median latency 3440 ms. English 11/13 (84.6%), Hindi 7/8 (87.5%), Marathi 6/7 (85.7%), Hinglish 5/6 (83.3%). Test split pass rate reached 76.9% (10/13) vs 53.8% before tuning.
- 2026-10-14 22:14 IST - [measurement] Completed manual tone scoring review across 10 sample replies for gemma2:2b across English, Hindi, Marathi, and Hinglish. Average tone score: 4.9/5.0. Natural phrasing, adherence to shop persona guidelines, and correct Devanagari script usage verified.
- 2026-10-14 23:40 IST - [measurement] Physical offline test verified with Wi-Fi off. Confirmed draft_reply and simulated customer chat generate full responses on localhost:8501 without internet connection. Zero external network calls confirmed.
- 2026-10-15 00:13 IST - [feature] Implemented SQLite FTS5 smart hybrid retrieval over products (db/fts.sql, engine/db.py, engine/retrieval.py). Real-time sync triggers on insert/update/delete, Unicode Devanagari query sanitization, and automatic scaling for large catalogues. Added live FTS5 search bar in UI catalogue editor. 35 unit tests pass.
- 2026-10-15 19:41 IST - [measurement] Benchmark run on gemma4:e2b (Gemma 4 Effective 2B Q4_K_M, 4.6 GB). ollama ps: 100% GPU offload on 6 GB RTX 3050 Laptop, NUM_CTX=4096. Test split results (13 cases): Overall pass rate 92.3% (12/13), facts_ok 12/13 (92.3%), needs_check_ok 13/13 (100.0%), language_ok 13/13 (100.0%), median latency 6287 ms. Hindi 2/2 (100.0%), Marathi 1/1 (100.0%), Hinglish 2/2 (100.0%), English 7/8 (87.5%). Report generated at eval/reports/latest_eval.md.
- 2026-10-15 19:49 IST - [measurement] Complete 34-case final benchmark on gemma4:e2b (Gemma 4 Effective 2B Q4_K_M, 4.6 GB). ollama ps: 100% GPU offload on 6 GB RTX 3050 Laptop, NUM_CTX=4096. Results: Overall pass rate 94.1% (32/34), facts_ok 33/34 (97.1%), needs_check_ok 34/34 (100.0%), language_ok 33/34 (97.1%), median latency 6389 ms. Hindi 8/8 (100.0%), Marathi 7/7 (100.0%), English 12/13 (92.3%), Hinglish 5/6 (83.3%). Dev split: 20/21 (95.2%), test split: 12/13 (92.3%). Zero safety failures, flawless Devanagari script preservation across all Hindi and Marathi queries. Detailed report: eval/reports/eval_gemma4_e2b_20261015_194915.md.
- 2026-10-15 21:10 IST - [fix] Executed surgical Bugfix and Polish pass across ReplyDesk. Upgraded verify_numeric_grounding to whitelist customer-echoed inquiry numbers and 2x to 10x price multiples. Tightened prompt injection regex to prevent false positives on benign shopping questions like "Can this long necklace act as a choker?". Made PII scrubber Order-ID and tracking safe (preserved tokens preceded by #, order, awb, utr, tracking, ref, invoice, id). Added multi-turn pronoun follow-up context expansion (prior_queries). Added SQLite embeddings_cache table and persistence helpers to eliminate cold-start redundant Ollama vector calls. Preserved seller-saved FAQs (source_type = 'seller_faq') across shop re-imports with replace=True and re-indexed into FTS5. Added reply_log telemetry persistence (routed_model, retrieval_mode, grounding_status, triage_badge) and displayed with html.escape() in history_page.py. Implemented force_model=True for pure single-model benchmarking in run_eval.py while recording would_route_to. Promoted gemma4:e2b as first-class selectable model in eval_page.py and settings_page.py. All 46 pytest tests pass in 12.83s, verify_shops.py passes 100%, zero em-dashes across repo.





