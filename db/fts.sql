-- Optional (stretch): full-text search over products for large catalogues.
-- Requires an SQLite build with FTS5. Check: PRAGMA compile_options;  (look for ENABLE_FTS5)
-- Not applied by init_db. Apply manually or from a separate "enable search" step.

CREATE VIRTUAL TABLE products_fts USING fts5 (
    name,
    description,
    content = 'products',
    content_rowid = 'id'
);

-- Backfill existing rows
INSERT INTO products_fts (rowid, name, description)
SELECT id, name, COALESCE(description, '') FROM products;

-- Keep the index in sync
CREATE TRIGGER trg_products_fts_ai AFTER INSERT ON products BEGIN
    INSERT INTO products_fts (rowid, name, description)
    VALUES (NEW.id, NEW.name, COALESCE(NEW.description, ''));
END;

CREATE TRIGGER trg_products_fts_ad AFTER DELETE ON products BEGIN
    INSERT INTO products_fts (products_fts, rowid, name, description)
    VALUES ('delete', OLD.id, OLD.name, COALESCE(OLD.description, ''));
END;

CREATE TRIGGER trg_products_fts_au AFTER UPDATE ON products BEGIN
    INSERT INTO products_fts (products_fts, rowid, name, description)
    VALUES ('delete', OLD.id, OLD.name, COALESCE(OLD.description, ''));
    INSERT INTO products_fts (rowid, name, description)
    VALUES (NEW.id, NEW.name, COALESCE(NEW.description, ''));
END;

-- Example: top 10 products for a customer message, for one seller
-- SELECT p.id, p.sku, p.name
-- FROM products_fts f JOIN products p ON p.id = f.rowid
-- WHERE products_fts MATCH ? AND p.seller_id = ?
-- ORDER BY rank LIMIT 10;
