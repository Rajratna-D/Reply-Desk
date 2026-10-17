-- ReplyDesk database schema (SQLite 3). See docs/DBMS.md for the explanation.
-- Apply once when PRAGMA user_version = 0. Every connection must also run:
--   PRAGMA foreign_keys = ON;

PRAGMA foreign_keys = ON;

CREATE TABLE sellers (
    id               INTEGER PRIMARY KEY,
    slug             TEXT    NOT NULL UNIQUE
                             CHECK (slug GLOB '[a-z0-9_]*' AND slug NOT GLOB '*[^a-z0-9_]*'),
    shop_name        TEXT    NOT NULL,
    description      TEXT,
    tone             TEXT    NOT NULL DEFAULT 'friendly',
    default_language TEXT    NOT NULL DEFAULT 'en'
                             CHECK (default_language IN ('en', 'hi', 'mr', 'hinglish')),
    created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE seller_languages (
    seller_id INTEGER NOT NULL REFERENCES sellers (id) ON DELETE CASCADE,
    language  TEXT    NOT NULL CHECK (language IN ('en', 'hi', 'mr', 'hinglish')),
    PRIMARY KEY (seller_id, language)
);

CREATE TABLE products (
    id           INTEGER PRIMARY KEY,
    seller_id    INTEGER NOT NULL REFERENCES sellers (id) ON DELETE CASCADE,
    sku          TEXT    NOT NULL,
    name         TEXT    NOT NULL,
    category     TEXT,
    description  TEXT,
    attributes   TEXT    NOT NULL DEFAULT '{}' CHECK (json_valid(attributes)),
    stock_status TEXT    NOT NULL DEFAULT 'in_stock'
                         CHECK (stock_status IN ('in_stock', 'low_stock', 'out_of_stock', 'made_to_order')),
    notes        TEXT,
    UNIQUE (seller_id, sku)
);

CREATE TABLE product_variants (
    id         INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products (id) ON DELETE CASCADE,
    label      TEXT    NOT NULL,
    price_inr  INTEGER NOT NULL CHECK (price_inr >= 0),
    UNIQUE (product_id, label)
);

CREATE TABLE policies (
    id          INTEGER PRIMARY KEY,
    seller_id   INTEGER NOT NULL REFERENCES sellers (id) ON DELETE CASCADE,
    topic       TEXT    NOT NULL
                        CHECK (topic IN ('delivery', 'returns', 'payment', 'hours', 'ordering', 'other')),
    title       TEXT    NOT NULL,
    body        TEXT    NOT NULL,
    source_type TEXT    NOT NULL DEFAULT 'config',
    UNIQUE (seller_id, topic, title)
);

CREATE TABLE sample_replies (
    id               INTEGER PRIMARY KEY,
    seller_id        INTEGER NOT NULL REFERENCES sellers (id) ON DELETE CASCADE,
    language         TEXT    NOT NULL CHECK (language IN ('en', 'hi', 'mr', 'hinglish')),
    customer_message TEXT    NOT NULL,
    reply            TEXT    NOT NULL,
    source_type      TEXT    NOT NULL DEFAULT 'config'
);

CREATE TABLE reply_log (
    id                 INTEGER PRIMARY KEY,
    seller_id          INTEGER NOT NULL REFERENCES sellers (id) ON DELETE CASCADE,
    customer_message   TEXT    NOT NULL,
    detected_language  TEXT    CHECK (detected_language IS NULL
                                      OR detected_language IN ('en', 'hi', 'mr', 'hinglish')),
    drafted_reply      TEXT    NOT NULL,
    needs_check        INTEGER NOT NULL DEFAULT 0 CHECK (needs_check IN (0, 1)),
    check_reason       TEXT,
    ungrounded_amounts TEXT    NOT NULL DEFAULT '[]' CHECK (json_valid(ungrounded_amounts)),
    risk_topics        TEXT    NOT NULL DEFAULT '[]' CHECK (json_valid(risk_topics)),
    model              TEXT    NOT NULL,
    latency_ms         INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    seller_action      TEXT    CHECK (seller_action IS NULL
                                      OR seller_action IN ('sent_as_is', 'edited', 'discarded')),
    final_reply        TEXT,
    routed_model       TEXT,
    retrieval_mode     TEXT,
    grounding_status   TEXT,
    triage_badge       TEXT,
    created_at         TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS embeddings_cache (
    seller_id   INTEGER NOT NULL,
    item_key    TEXT    NOT NULL,
    text_hash   TEXT    NOT NULL,
    vector_json TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (seller_id, item_key, text_hash)
);

CREATE TABLE eval_runs (
    id          INTEGER PRIMARY KEY,
    model       TEXT NOT NULL,
    notes       TEXT,
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT
);

CREATE TABLE eval_results (
    id               INTEGER PRIMARY KEY,
    run_id           INTEGER NOT NULL REFERENCES eval_runs (id) ON DELETE CASCADE,
    case_id          TEXT    NOT NULL,
    shop_slug        TEXT    NOT NULL,
    language         TEXT    NOT NULL CHECK (language IN ('en', 'hi', 'mr', 'hinglish')),
    category         TEXT,
    split            TEXT    CHECK (split IS NULL OR split IN ('dev', 'test')),
    reply            TEXT    NOT NULL,
    needs_check      INTEGER NOT NULL CHECK (needs_check IN (0, 1)),
    facts_ok         INTEGER NOT NULL CHECK (facts_ok IN (0, 1)),
    needs_check_ok   INTEGER NOT NULL CHECK (needs_check_ok IN (0, 1)),
    language_ok      INTEGER NOT NULL CHECK (language_ok IN (0, 1)),
    language_label_ok INTEGER CHECK (language_label_ok IS NULL OR language_label_ok IN (0, 1)),
    latency_ms       INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    prompt_tokens    INTEGER,
    output_tokens    INTEGER,
    tone_score       INTEGER CHECK (tone_score IS NULL OR tone_score BETWEEN 1 AND 5),
    numeric_grounding_ok INTEGER CHECK (numeric_grounding_ok IS NULL OR numeric_grounding_ok IN (0, 1)),
    retrieval_mode   TEXT,
    UNIQUE (run_id, case_id)
);

CREATE INDEX idx_products_seller        ON products (seller_id);
CREATE INDEX idx_variants_product       ON product_variants (product_id);
CREATE INDEX idx_policies_seller        ON policies (seller_id);
CREATE INDEX idx_samples_seller         ON sample_replies (seller_id, language);
CREATE INDEX idx_reply_log_seller_time  ON reply_log (seller_id, created_at DESC);
CREATE INDEX idx_eval_results_run       ON eval_results (run_id);

CREATE TRIGGER trg_sellers_touch
AFTER UPDATE ON sellers
FOR EACH ROW
BEGIN
    UPDATE sellers SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE VIEW v_catalog AS
SELECT s.id          AS seller_id,
       s.slug        AS seller_slug,
       p.id          AS product_id,
       p.sku         AS sku,
       p.name        AS product_name,
       p.category    AS category,
       p.attributes  AS attributes,
       p.stock_status AS stock_status,
       p.notes       AS notes,
       v.label       AS variant_label,
       v.price_inr   AS price_inr
FROM sellers s
JOIN products p         ON p.seller_id = s.id
JOIN product_variants v ON v.product_id = p.id;

PRAGMA user_version = 1;
