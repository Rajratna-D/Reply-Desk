# Tasks

Dates are IST. Challenge deadline: 18 Oct 11:59 PM PDT (19 Oct about 12:29 PM IST). Aim to submit on the evening of 18 Oct.

Rule: work one milestone at a time. Tick boxes as you finish. Add a dated line to `docs/BUILD_LOG.md` after each milestone.

## M0 — Setup (14 Oct)

- [ ] Create the git repo. First commit must be on or after 12 Oct (challenge window).
- [ ] Add `.gitignore`, `requirements.txt` (`streamlit`, `ollama`, `jsonschema`, `pytest`, `python-dotenv`).
- [ ] Install Ollama, pull the smallest Gemma 4 tag, confirm it answers from the command line.
- [ ] Record hardware, tag names, and `ollama ps` output in `docs/SETUP.md` and `docs/BUILD_LOG.md`.
- [ ] Send messages to 10 to 15 possible sellers (see "First user" below).

## M1 — Engine core (14 to 15 Oct)

- [ ] `engine/config.py`: settings from environment.
- [ ] `engine/db.py`: `init` creates the database from `db/schema.sql`; connection helper with `PRAGMA foreign_keys = ON`.
- [ ] `engine/importer.py`: import and export seller JSON (validate against `config/seller.schema.json`).
- [ ] `engine/retrieval.py`: build catalogue and policy context for a seller.
- [ ] `engine/prompt.py`: build the system prompt and few-shot examples from `docs/PROMPTS.md`.
- [ ] `engine/llm.py`: call Ollama with structured output; clear errors if Ollama is down or the model is missing.
- [ ] `engine/guardrails.py`: numeric grounding check and `needs_check` enforcement.
- [ ] `engine/service.py`: `draft_reply(seller_slug, message)` returns reply, language, needs_check, reason, latency.
- [ ] Tests for importer, retrieval, and guardrails (no model needed). A smoke test that calls the model, skipped if Ollama is not running.
- [ ] Done when: running `draft_reply` from a script on the three sample shops gives sensible replies.

## M2 — UI (15 to 16 Oct)

- [ ] `app.py` with pages: Reply, Setup, History, Settings.
- [ ] Setup page: shop details, products (form and CSV), policies, sample replies, import/export JSON.
- [ ] Reply page: paste message, generate, needs-check banner, editable draft, copy, mark sent/edited/discarded.
- [ ] Shop selector. Friendly error if Ollama is not running.
- [ ] Done when: a non-technical person could set up a shop and get a reply without help.

## M3 — Evaluation (16 Oct)

- [ ] `eval/run_eval.py` runs every case in `eval/questions.json` and writes to `eval_runs` / `eval_results` plus a CSV and markdown report.
- [ ] Run on the smallest model, then the next size up. Record results in `docs/BUILD_LOG.md`.
- [ ] Review failures by hand, especially Hindi and Marathi. Fix the biggest problems in the prompt or guardrails and re-run.
- [ ] Manual tone scores (1 to 5) on a sample of replies.
- [ ] Offline test with Wi-Fi off.

## First user (14 to 17 Oct, in parallel)

- [ ] Messages sent to possible sellers (family, classmates' families, small Instagram shops).
- [ ] If a seller agrees: get a product list (about 10 products), policies, and 10 to 20 typical customer questions. Do not collect real customer chats or personal details.
- [ ] Let them try it. Record what they said, whether they would pay, and what they asked for next. Real quotes only, with permission.
- [ ] If nobody replies by 16 Oct: use the fictional sample shops and say so clearly in the post. Do not invent a user.

## Hack Day — 17 Oct (Pune, in person)

- [ ] This is a separate event with its own challenge revealed on the day. Use it to learn and network. Anything built there is a separate project and is not part of this submission unless it was genuinely started and finished inside the challenge window and fits the theme.
- [ ] Evening: gather any seller feedback.

## M4 — Write-up and submit (17 to 18 Oct)

- [ ] Optional: demo hosting. If using a `.tech` domain, claim it at hacktoberfest.com/my/promos.
- [ ] Record a 2 to 3 minute demo video: setup a shop, paste a Hindi/Marathi/Hinglish message, show the needs-check case, show it working offline.
- [ ] README: what it is, install steps, how to run the eval, honest limitations, note any commits after the deadline.
- [ ] Write the DEV post from `docs/BUILD_LOG.md`. Use the template sections. Lead with who the seller is and what their problem was; show real numbers and real failures; explain why open models mattered.
- [ ] Choose prize categories honestly (Gemma yes; others only if really used).
- [ ] Submit with time to spare (evening 18 Oct IST).

## Stretch (only if everything above is done)

- [ ] FTS5 retrieval for large catalogues (`db/fts.sql`).
- [ ] Quick fine-tune or prompt-tuning comparison for Marathi.
- [ ] Save the agent session with DevRelay and embed it in the post.
- [ ] Export a shop to a printable FAQ sheet.
