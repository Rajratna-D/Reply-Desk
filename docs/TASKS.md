# Tasks

Dates are IST. Challenge deadline: 18 Oct 11:59 PM PDT (19 Oct about 12:29 PM IST). Aim to submit on the evening of 18 Oct.

Rule: work one milestone at a time. Tick boxes as you finish. Add a dated line to `docs/BUILD_LOG.md` after each milestone.

## M0 - Setup (14 Oct)

- [x] Create the git repo. First commit must be on or after 12 Oct (challenge window).
- [x] Add `.gitignore`, `requirements.txt` (`streamlit`, `ollama`, `jsonschema`, `pytest`, `python-dotenv`).
- [x] Install Ollama, pull the smallest model tag, confirm it answers from the command line.
- [x] Record hardware, tag names, and `ollama ps` output in `docs/SETUP.md` and `docs/BUILD_LOG.md`.
- [ ] Send messages to 10 to 15 possible sellers (see "First user" below).

## M1 - Engine core (14 to 15 Oct)

- [x] `engine/config.py`: settings from environment.
- [x] `engine/db.py`: `init` creates the database from `db/schema.sql`; connection helper with `PRAGMA foreign_keys = ON`.
- [x] `engine/importer.py`: import and export seller JSON (validate against `config/seller.schema.json`).
- [x] `engine/retrieval.py`: build catalogue and policy context for a seller.
- [x] `engine/prompt.py`: build the system prompt and few-shot examples from `docs/PROMPTS.md`.
- [x] `engine/llm.py`: call Ollama with structured output; clear errors if Ollama is down or the model is missing.
- [x] `engine/guardrails.py`: numeric grounding check and `needs_check` enforcement.
- [x] `engine/service.py`: `draft_reply(seller_slug, message)` returns reply, language, needs_check, reason, latency.
- [x] Tests for importer, retrieval, and guardrails (no model needed). A smoke test that calls the model, skipped if Ollama is not running.
- [x] Done when: running `draft_reply` from a script on the three sample shops gives sensible replies.

## M2 - UI (15 to 16 Oct)

- [x] `app.py` with pages: Reply, Setup, History, Settings, plus Customer Chat (simulated) and Owner Inbox.
- [x] Setup page: shop details, products (form and CSV), policies, sample replies, import/export JSON.
- [x] Reply page: paste message, generate, needs-check banner, editable draft, copy, mark sent/edited/discarded.
- [x] Customer Chat page (simulated demo): select shop, type message in En/Hi/Mr/Hinglish, immediate draft generation, pending status in `reply_log`, memory session tracking in `st.session_state`, "Simulated chat for demo" label.
- [x] Owner Inbox page: pending drafts queue (`seller_action IS NULL`), customer message, editable draft, needs-check & risk warnings, action buttons (Send as is, Send edited, Discard), refresh button & `st.fragment(run_every=...)`.
- [x] Shop selector (switches active shop without login; replies never cross shop boundaries).
- [x] Friendly error if Ollama is not running or model is missing.
- [x] Side-by-side demo verification (two localhost windows: owner left, customer right).
- [x] Done when: a non-technical person could set up a shop, receive simulated messages in their inbox, and review/send replies without help.

## M3 - Evaluation (16 Oct)

- [x] `eval/run_eval.py` runs every case in `eval/questions.json` and writes to `eval_runs` / `eval_results` plus a CSV and markdown report.
- [x] Run on the smallest model, then the next size up. Record results in `docs/BUILD_LOG.md`.
- [ ] Review failures by hand, especially Hindi and Marathi. Fix the biggest problems in the prompt or guardrails and re-run.
- [ ] Manual tone scores (1 to 5) on a sample of replies.
- [ ] Offline test with Wi-Fi off.

## First user (14 to 17 Oct, in parallel)

- [ ] Messages sent to possible sellers (family, classmates' families, small Instagram shops).
- [ ] If a seller agrees: get a product list (about 10 products), policies, and 10 to 20 typical customer questions. Do not collect real customer chats or personal details.
- [ ] Let them try it. Record what they said, whether they would pay, and what they asked for next. Real quotes only, with permission.
- [ ] If nobody replies by 16 Oct: use the fictional sample shops and say so clearly in the post. Do not invent a user.

## Hack Day - 17 Oct (Pune, in person)

- [ ] This is a separate event with its own challenge revealed on the day. Use it to learn and network. Anything built there is a separate project and is not part of this submission unless it was genuinely started and finished inside the challenge window and fits the theme.
- [ ] Evening: gather any seller feedback.

## M4 - Write-up and submit (17 to 18 Oct)

- [ ] Optional: demo hosting. If using a `.tech` domain, claim it at hacktoberfest.com/my/promos.
- [ ] Record a 2 to 3 minute demo video using two browser windows side by side (owner left, customer right).
- [ ] README: what it is, install steps, how to run the eval, honest limitations, note any commits after the deadline.
- [ ] Write the DEV post from `docs/BUILD_LOG.md`. Use the template sections. Lead with who the seller is and what their problem was; show real numbers and real failures; explain why open models mattered.
- [ ] Choose prize categories honestly (Gemma yes; others only if really used).
- [ ] Submit with time to spare (evening 18 Oct IST).

### Demo script (2 to 3 minute screen recording, side-by-side windows: Owner left, Customer right)
- a. In the owner window, set up or open a shop on the Setup page (show products, prices, policies).
- b. In the customer window, send a normal question (for example a price or delivery question). Show the draft appearing in the owner inbox, edit it, send it, and show it arriving in the customer chat.
- c. Send a question the shop data does not cover (for example custom work or a gluten allergy). Show the needs-check banner and the "I'll check" reply.
- d. Switch to a second shop and send a Hindi, Marathi or Hinglish message to show it works for any seller and matches the customer's language.
- e. Turn Wi-Fi off and send one more message to show it runs locally.
- Note: Record the model tag and the latency shown during the demo in `docs/BUILD_LOG.md` (real measurements only).

## Stretch (only if everything above is done)

- [ ] FTS5 retrieval for large catalogues (`db/fts.sql`).
- [ ] Quick fine-tune or prompt-tuning comparison for Marathi.
- [ ] Save the agent session with DevRelay and embed it in the post.
- [ ] Export a shop to a printable FAQ sheet.
