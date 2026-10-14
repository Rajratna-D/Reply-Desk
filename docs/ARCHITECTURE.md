# Architecture — ReplyDesk

This document is about code structure: modules, interfaces, and folders. For the why, see `SYSTEM_DESIGN.md`. For tables, see `DBMS.md`.

## Folder layout

```
replydesk/
├── AGENTS.md
├── README.md
├── requirements.txt
├── .env.example
├── app.py                     # Streamlit entry point (navigation + shared sidebar)
├── ui/
│   ├── reply_page.py          # paste message, draft, flags, copy, mark action
│   ├── setup_page.py          # shop details, products, policies, samples, import/export
│   ├── history_page.py        # past drafts
│   └── settings_page.py       # model name, Ollama status, clear history
├── engine/
│   ├── __init__.py
│   ├── config.py              # Settings from environment
│   ├── db.py                  # connection, init, CRUD helpers
│   ├── importer.py            # JSON and CSV import, JSON export
│   ├── retrieval.py           # build catalogue/policy context for a seller
│   ├── prompt.py              # system prompt and messages
│   ├── llm.py                 # Ollama client, structured output, errors
│   ├── guardrails.py          # amount grounding, risk topics, language script check
│   └── service.py             # draft_reply orchestration
├── db/
│   ├── schema.sql
│   └── fts.sql                # optional FTS5 setup (stretch)
├── config/
│   ├── seller.schema.json
│   ├── urban_thread.json
│   ├── sweet_crumbs.json
│   └── kalakruti_jewels.json
├── eval/
│   ├── questions.json
│   ├── run_eval.py
│   └── results/               # generated, git-ignored
├── tests/
├── docs/
└── .agent/
    ├── rules/
    └── workflows/
```

## Module responsibilities and interfaces

Signatures are the contract. Keep them stable so tests and UI do not break.

### `engine/config.py`

```python
@dataclass(frozen=True)
class Settings:
    model_name: str
    ollama_host: str = "http://localhost:11434"
    num_ctx: int = 4096
    db_path: str = "data/replydesk.db"
    temperature: float = 0.2

def load_settings() -> Settings: ...
```
Reads environment variables (and `.env` if present). `model_name` has no hardcoded default; raise a clear error if unset.

### `engine/db.py`

```python
def connect(db_path: str | None = None) -> sqlite3.Connection: ...   # row_factory = sqlite3.Row, PRAGMA foreign_keys = ON
def init_db(db_path: str | None = None) -> None: ...                  # applies db/schema.sql if user_version == 0
def get_seller_by_slug(conn, slug: str) -> sqlite3.Row | None: ...
def list_sellers(conn) -> list[sqlite3.Row]: ...
def log_reply(conn, seller_id: int, **fields) -> int: ...
def set_reply_action(conn, reply_id: int, action: str, final_reply: str | None) -> None: ...
def clear_history(conn, seller_id: int) -> int: ...
```
All SQL parameterized. See `DBMS.md` for schema and migration rules (`PRAGMA user_version`).

### `engine/importer.py`

```python
def validate_config(data: dict) -> None: ...                  # jsonschema; raises ConfigError
def import_config(conn, data: dict, *, replace: bool = False) -> int: ...   # returns seller_id; one transaction
def export_config(conn, slug: str) -> dict: ...               # same shape as import
def import_products_csv(conn, slug: str, csv_path: str) -> int: ...
```
Import runs inside one transaction. If `replace` is true, the seller's products, policies, and samples are deleted and reinserted. Round trip `import -> export -> import` must be lossless (tested).

### `engine/retrieval.py`

```python
@dataclass
class Context:
    shop: dict                 # name, description, tone, default_language, languages
    catalogue_block: str
    policies_block: str
    examples: list[dict]       # sample replies (language, customer_message, reply)
    known_amounts: set[int]    # every price and every number that appears in a rupee context in the data

def build_context(conn, seller_id: int, message: str | None = None, *, max_products: int = 40) -> Context: ...
```
v1: include every product (up to `max_products`). Stretch: when over the limit, use FTS5 on `message` to pick top-k.

### `engine/prompt.py`

```python
def build_messages(ctx: Context, customer_message: str) -> list[dict]: ...   # [{"role":"system",...},{"role":"user",...}]
RESPONSE_SCHEMA: dict   # JSON schema for {reply, language, needs_check, reason}
```
Prompt text is defined in `docs/PROMPTS.md`. Keep code and doc in sync.

### `engine/llm.py`

```python
class OllamaUnavailable(Exception): ...
class ModelMissing(Exception): ...
class BadModelOutput(Exception): ...

def generate_json(messages: list[dict], schema: dict, *, model: str, host: str,
                  num_ctx: int, temperature: float) -> dict: ...
def ollama_status(host: str) -> dict: ...     # reachable?, models available
```
Uses structured output when available. On invalid JSON: retry once, then raise `BadModelOutput`.

### `engine/guardrails.py`

```python
def extract_amounts(text: str) -> list[int]: ...          # "₹1,200", "Rs 899", "899 rupees", "1200/-"
def ungrounded_amounts(reply: str, known: set[int]) -> list[int]: ...
def risk_topics(message: str) -> list[str]: ...           # allergy, health, discount, wholesale, custom, personal
def script_of(text: str) -> str: ...                      # "devanagari" | "latin" | "mixed"
```
Amount parsing must handle commas, `₹`, `Rs`, `Rs.`, `INR`, `/-`, and Devanagari digits. Risk topic keywords cover English, Hindi, Marathi, and Hinglish; keep the keyword lists in one constant, documented in `PROMPTS.md`.

### `engine/service.py`

```python
@dataclass
class Draft:
    reply: str
    language: str
    needs_check: bool
    reason: str
    ungrounded_amounts: list[int]
    risk_topics: list[str]
    model: str
    latency_ms: int
    reply_id: int | None

def draft_reply(seller_slug: str, message: str, *, model: str | None = None, log: bool = True) -> Draft: ...
```
Steps: load seller, build context, build messages, call model, run guardrails (if ungrounded amounts exist, set `needs_check = True` and append to `reason`), measure latency, log, return. It never sends anything.

### `eval/run_eval.py`

```
python -m eval.run_eval --model <tag> [--notes "..."] [--shop <slug>] [--limit N]
```
Loads `eval/questions.json`, imports sample shops into a temporary database (so eval never touches real data), runs `draft_reply(log=False)` per case, scores, writes `eval_runs` / `eval_results`, and writes `eval/results/<run>.csv` and `.md`. Scoring rules are in `EVAL_PLAN.md`.

## UI pages (Streamlit)

- Sidebar: shop selector, model name, Ollama status indicator.
- Reply page: text area for customer message, Draft button (spinner), draft in an editable text area, copy button, flags (needs-check, ungrounded amounts, risk topics), buttons "Sent as is", "Edited", "Discard".
- Setup page: tabs for Shop, Products, Policies, Sample replies, Import/Export.
- History page: table of past drafts with filters.
- Settings page: model tag (with list of installed models from Ollama), clear history.

Keep page functions thin; all logic lives in `engine/`.

## Dependencies

`streamlit`, `ollama` (Python client) or plain `requests`/`httpx` against the Ollama HTTP API, `jsonschema`, `pytest`, `python-dotenv`. Ask before adding anything else.

## Data flow summary

1. Import or enter shop data -> SQLite.
2. Draft request -> `service.draft_reply` -> `retrieval.build_context` -> `prompt.build_messages` -> `llm.generate_json` -> `guardrails` -> `db.log_reply`.
3. Seller action -> `db.set_reply_action`.
4. Export shop -> `importer.export_config`.
