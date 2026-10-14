-- SQLite FTS5 full-text search over products for catalogue scaling.
-- Requires an SQLite build with FTS5. Check: PRAGMA compile_options; (look for ENABLE_FTS5)

CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5 (
    name,
    category,
    description,
    notes,
    content = 'products',
    content_rowid = 'id'
);

-- Backfill existing products into FTS index
INSERT OR REPLACE INTO products_fts (rowid, name, category, description, notes)
SELECT id, name, COALESCE(category, ''), COALESCE(description, ''), COALESCE(notes, '')
FROM products;

-- Keep the FTS index in real-time sync with products table
CREATE TRIGGER IF NOT EXISTS trg_products_fts_ai AFTER INSERT ON products BEGIN
    INSERT INTO products_fts (rowid, name, category, description, notes)
    VALUES (NEW.id, NEW.name, COALESCE(NEW.category, ''), COALESCE(NEW.description, ''), COALESCE(NEW.notes, ''));
END;

CREATE TRIGGER IF NOT EXISTS trg_products_fts_ad AFTER DELETE ON products BEGIN
    INSERT INTO products_fts (products_fts, rowid, name, category, description, notes)
    VALUES ('delete', OLD.id, OLD.name, COALESCE(OLD.category, ''), COALESCE(OLD.description, ''), COALESCE(OLD.notes, ''));
END;

CREATE TRIGGER IF NOT EXISTS trg_products_fts_au AFTER UPDATE ON products BEGIN
    INSERT INTO products_fts (products_fts, rowid, name, category, description, notes)
    VALUES ('delete', OLD.id, OLD.name, COALESCE(OLD.category, ''), COALESCE(OLD.description, ''), COALESCE(OLD.notes, ''));
    INSERT INTO products_fts (rowid, name, category, description, notes)
    VALUES (NEW.id, NEW.name, COALESCE(NEW.category, ''), COALESCE(NEW.description, ''), COALESCE(NEW.notes, ''));
END;
