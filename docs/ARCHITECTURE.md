# Architecture - ReplyDesk

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
│   ├── inbox_page.py          # owner inbox: pending drafts queue, review/send/discard
│   ├── customer_chat_page.py  # simulated customer chat for side-by-side demo
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
│   └── fts.sql                # SQLite FTS5 setup and sync triggers
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
def validate_ollama_url(url: str) -> str: ...  # SSRF protection: restricts endpoint to localhost/127.0.0.1
```
Reads environment variables (and `.env` if present). `validate_ollama_url` enforces local loopback binding to block server-side request forgery.

### `engine/db.py`

```python
def connect(db_path: str | None = None) -> sqlite3.Connection: ...   # row_factory = sqlite3.Row, PRAGMA foreign_keys = ON
def init_db(db_path: str | None = None) -> None: ...                  # applies db/schema.sql and db/fts.sql
def get_seller_by_slug(conn, slug: str) -> sqlite3.Row | None: ...
def list_sellers(conn) -> list[sqlite3.Row]: ...
def log_reply(conn, seller_id: int, **fields) -> int: ...
def set_reply_action(conn, reply_id: int, action: str, final_reply: str | None) -> None: ...
def save_faq_pair(conn, seller_id: int, question: str, reply: str, topic: str = "other", language: str = "en") -> int: ...  # 1-click FAQ persistence
def get_cached_embedding(conn, seller_id: int, item_key: str, text_hash: str) -> list[float] | None: ...
def save_cached_embedding(conn, seller_id: int, item_key: str, text_hash: str, vector: list[float]) -> None: ...
def clear_history(conn, seller_id: int) -> int: ...
```
All SQL parameterized. Supports FTS5 virtual tables with real-time sync triggers and persistent SQLite embeddings cache.

### `engine/importer.py`

```python
def validate_config(data: dict) -> None: ...                  # jsonschema; raises ConfigError
def import_config(conn, data: dict, *, replace: bool = False) -> int: ...   # returns seller_id; preserves seller_faq rows
def export_config(conn, slug: str) -> dict: ...               # same shape as import
def import_products_csv(conn, slug: str, csv_path: str) -> int: ...
```
Import runs inside one transaction. If `replace` is true, config data is refreshed while all merchant-added `seller_faq` policies and samples survive and re-index. Round trip `import -> export -> import` is verified lossless.

### `engine/retrieval.py`

```python
@dataclass
class Context:
    shop: dict                 # name, description, tone, default_language, languages
    catalogue_block: str
    policies_block: str
    examples: list[dict]       # sample replies (language, customer_message, reply)
    known_amounts: set[int]    # every price and every number that appears in a rupee context in the data
    retrieved_products: list[dict] = field(default_factory=list)
    retrieval_mode: str = "fts5_bm25"

def build_context(conn, seller_id: int, message: str | None = None, *, top_k: int = 15, prior_queries: list[str] | None = None) -> Context: ...
def reciprocal_rank_fusion(bm25_ranked: list[dict], vector_ranked: list[dict], k: int = 60) -> list[dict]: ...
def pure_cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float: ...
```

Hybrid RRF retrieval: combines SQLite FTS5 BM25 keyword matching with local embedding vector search (pure Python cosine similarity, zero external ML dependencies). Expands short follow-up and pronoun queries using `prior_queries`. Falls back gracefully to BM25 or full catalogue when offline.

### `engine/prompt.py`

```python
def build_messages(ctx: Context, customer_message: str, tone_override: str | None = None) -> list[dict]: ...
RESPONSE_SCHEMA: dict   # JSON schema for {reply, language, needs_check, reason}
```
Prompt text isolates untrusted customer text using `<untrusted_customer_message>` XML tags to prevent indirect prompt injection, and supports dynamic tone overrides.

### `engine/llm.py`

```python
class OllamaUnavailable(Exception): ...
class ModelMissing(Exception): ...
class BadModelOutput(Exception): ...

def generate_json(messages: list[dict], schema: dict, *, model: str, fallback_model: str | None = None,
                  host: str, num_ctx: int, temperature: float) -> dict: ...
def ollama_status(host: str) -> dict: ...     # reachable?, models available
```
Structured JSON output with retry logic and automated local fallback when a secondary model tier is missing.

### `engine/guardrails.py`

```python
def redact_pii(text: str) -> tuple[str, list[str]]: ...          # masks cards, IDs, contact details while preserving order numbers
def detect_prompt_injection(text: str) -> tuple[bool, str]: ...   # jailbreak, override, instruction leaking
def verify_numeric_grounding(draft_reply: str, source_context: str, customer_query: str = "") -> dict: ...
def extract_amounts(text: str) -> list[int]: ...                  # "₹1,200", "Rs 899", "899 rupees", "1200/-"
def ungrounded_amounts(reply: str, known: set[int]) -> list[int]: ...
def risk_topics(message: str) -> list[str]: ...                   # allergy, health, discount, wholesale, custom, personal
def script_of(text: str) -> str: ...                              # "devanagari" | "latin" | "mixed"
```
Precompiled regexes for zero-false-positive risk detection and comprehensive numeric grounding verification with query number echoing and 2x to 10x quantity multiplier support.

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
    reply_id: int | None = None
    routed_model: str | None = None
    actual_model: str | None = None
    fallback_used: bool = False
    route_reason: str = ""
    retrieval_mode: str = "fts5_bm25"
    unverified_numbers: list[str] = field(default_factory=list)
    needs_human_review: bool | None = None
    would_route_to: str | None = None
    grounding_status: str | None = None
    triage_badge: str | None = None

def select_gemma_model(query: str, retrieved_chunks: list[Any], default_model: str = "gemma2:2b") -> dict[str, Any]: ...
def draft_reply(seller_slug: str, message: str, *, model: str | None = None, log: bool = True,
                force_model: bool = False, prior_queries: list[str] | None = None,
                tone_override: str | None = None) -> Draft: ...
```
End-to-end orchestration: PII scrubbing, injection short-circuiting, context building, model routing, schema-guided generation, numeric verification, and logging. It never sends anything automatically.

### `eval/run_eval.py`

```
python -m eval.run_eval --model <tag> [--split dev|test|all] [--notes "..."] [--shop <slug>]
```
Loads `eval/questions.json`, imports sample shops into a temporary database, runs `draft_reply(log=False)` per case, scores facts/safety/language, and writes timestamped report files into `eval/reports/`.

## UI pages (Streamlit)

- Sidebar: shop selector (switches active seller without login), model name, Ollama status indicator.
- Customer Chat page (`ui/customer_chat_page.py`): Simulated WhatsApp-style messenger frame for split-screen demo. Shop selector, multilingual customer input, real-time message exchange simulation.
- Owner Inbox page (`ui/inbox_page.py`): Message triage queue for shop owners. Confidence badges (`AUTO-DRAFT READY`, `POLICY CHECK`, `NEEDS HUMAN`), editable drafts, grounding alerts, and quick actions ("Send as is", "Send edited", "Discard").
- Reply page (`ui/reply_page.py`): Manual scratchpad with Reply Tone Switcher (*Warm Boutique*, *Concise WhatsApp*, *Polite Hinglish*), live engine telemetry bar, and 1-Click FAQ saving into shop policies.
- Setup page (`ui/setup_page.py`): Tabs for Shop, Products (with live FTS5 search), Policies, Sample replies, and Import/Export.
- History page (`ui/history_page.py`): Table of past drafts with status filters.
- Settings page (`ui/settings_page.py`): Model inventory, SSRF security status, hardware offload telemetry, and history purge.

Keep page functions thin; all logic lives in `engine/`.

## Dependencies

`streamlit`, `ollama` (Python client) or plain `requests`/`httpx` against the Ollama HTTP API, `jsonschema`, `pytest`, `python-dotenv`. Ask before adding anything else.

## Data flow summary

1. Import or enter shop data -> SQLite.
2. Manual Draft request -> `service.draft_reply` -> `retrieval.build_context` -> `prompt.build_messages` -> `llm.generate_json` -> `guardrails` -> `db.log_reply` (pending or logged).
3. Simulated Chat flow: Customer sends message -> `service.draft_reply` -> logged in `reply_log` with `seller_action = NULL` -> customer sees "The shop will reply shortly." -> Owner Inbox loads pending drafts -> Owner edits/approves ("Send") -> `db.set_reply_action` -> Customer Chat displays `final_reply` (or `drafted_reply`).
4. Seller action -> `db.set_reply_action`.
5. Export shop -> `importer.export_config`.
