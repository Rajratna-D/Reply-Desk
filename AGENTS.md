# AGENTS.md - ReplyDesk

Read this file first, then the docs listed under "Read next". Do not start coding until you have summarized the project back to the user and proposed a plan.

## What this project is

ReplyDesk is a local-first assistant that drafts customer replies for small sellers (Instagram / WhatsApp shops). A seller sets up their shop once (products, prices, policies, tone, languages). When a customer message arrives, the seller pastes it in and ReplyDesk drafts a reply in the customer's language (English, Hindi, Marathi, or Hinglish), using only the seller's own data. The seller reviews and sends it. Nothing is ever sent automatically.

It is an entry for the DEV / MLH Hacktoberfest 2026 Open-Source AI Challenge, Week 2, theme "Side Hustle" (see `docs/CHALLENGE.md`). The open-source AI must be what makes it work, and we must be able to prove why that matters (private, offline, free per reply, swappable model, per-seller customization).

## Stack

- Python 3.11+
- Ollama serving an open-weight Gemma 4 model locally (model name comes from settings, never hardcoded)
- SQLite (stdlib `sqlite3`) for storage; schema in `db/schema.sql`
- Streamlit for the UI
- `pytest` for tests, `jsonschema` for config validation
- No other dependencies without asking the user first

## Commands

```
pip install -r requirements.txt
ollama serve                         # in a separate terminal
python -m engine.db init             # create the database from db/schema.sql
python -m engine.importer config/urban_thread.json
streamlit run app.py
python -m eval.run_eval --model <tag> --notes "short note"
pytest
```

(These commands describe the target. If a command does not exist yet, creating it is part of the task list in `docs/TASKS.md`.)

## Hard rules

1. **Local only.** The app must make no network calls except to the local Ollama server (`OLLAMA_HOST`, default `http://localhost:11434`). No cloud LLM APIs, no telemetry, no CDN assets needed at runtime.
2. **Grounded replies only.** Every price, size, colour, stock status, delivery time, and policy in a reply must come from the seller's data. If the answer is not in the data, the reply must say the shop will check and get back, and `needs_check` must be true. Never guess. Allergy, health, and safety questions not covered by the data always set `needs_check`.
3. **Draft only.** The app never sends messages anywhere. The seller always reviews.
4. **Model is a setting.** `MODEL_NAME` comes from the environment or settings. Swapping models must require no code change.
5. **Match the customer.** Reply in the customer's language and script. Hinglish (Romanized Hindi) gets a Romanized reply. Devanagari gets Devanagari.
6. **Keep scope small.** No login, no accounts, no WhatsApp/Instagram integration, no payments, no analytics dashboards. See "Out of scope" in `docs/PRD.md`.
7. **Do not invent facts about the project.** Do not claim benchmark results, latency, or user feedback that have not been measured and recorded in `docs/BUILD_LOG.md`.
8. **Ask before** adding a dependency, changing the database schema, or changing the config format. Schema changes need a migration note in `docs/DBMS.md`.
9. **No em dashes.** Never use em dashes (`—`) anywhere in this project (code, UI text, markdown, commit messages). Use standard hyphens (`-`), colons, or commas instead. See `.agent/rules/no-em-dash.md`.

## Conventions

- Type hints on public functions. Small functions. Docstrings that say *why*, not *what*.
- SQL is always parameterized. Never build SQL with string formatting.
- Prompts live in `engine/prompt.py` and are documented in `docs/PROMPTS.md`. Keep the two in sync.
- Commit small and often with clear messages. The challenge requires the project to be started and finished inside the challenge window, so the git history matters.
- After any meaningful decision, bug, fix, or measurement, add a dated line to `docs/BUILD_LOG.md`.

## Read next

| File | Why |
|---|---|
| `docs/CHALLENGE.md` | What the challenge asks for and how it is judged |
| `docs/PRD.md` | What to build, for whom, and acceptance criteria |
| `docs/SYSTEM_DESIGN.md` | Requirements, data flow, failure modes, trade-offs |
| `docs/ARCHITECTURE.md` | Modules, interfaces, folder layout |
| `docs/DBMS.md` | Tables, constraints, indexes, queries |
| `docs/CONFIG_SCHEMA.md` | Seller config format (JSON) and how it maps to the database |
| `docs/PROMPTS.md` | System prompt, output format, examples |
| `docs/EVAL_PLAN.md` | How replies are tested and scored |
| `docs/TASKS.md` | Ordered milestones and dates |
| `docs/SETUP.md` | Hardware, Ollama, model choice |

## Working style

- Work one milestone at a time from `docs/TASKS.md`. Tick it off when done and run the relevant tests.
- When something in the docs is ambiguous or contradicts the code, stop and ask rather than guessing.
- Prefer the simplest thing that satisfies the acceptance criteria. This is a 5-day build.
