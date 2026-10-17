"""Importer and exporter for seller JSON and CSV product catalogues."""

import csv
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any
import jsonschema

from engine.db import connect, get_seller_by_slug, is_fts5_available

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "config" / "seller.schema.json"


class ConfigError(Exception):
    """Raised when seller configuration is invalid or violates schema/business rules."""


def validate_config(data: dict[str, Any]) -> None:
    """Validate seller config dictionary against schema and business rules."""
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found at {SCHEMA_PATH}")

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as err:
        raise ConfigError(f"Config schema validation failed: {err.message}") from err

    shop = data.get("shop", {})
    slug = shop.get("slug", "")
    if not re.match(r"^[a-zA-Z0-9_-]{1,50}$", slug):
        raise ConfigError(
            f"Invalid shop slug '{slug}'. Must be 1 to 50 alphanumeric characters, hyphens, or underscores."
        )

    default_lang = shop.get("default_language")
    languages = shop.get("languages", [])

    if default_lang not in languages:
        raise ConfigError(
            f"default_language '{default_lang}' must be included in supported languages: {languages}"
        )

    products = data.get("products", [])
    if not products:
        raise ConfigError("Config must contain at least one product.")

    skus = set()
    for prod in products:
        sku = prod.get("sku")
        if sku in skus:
            raise ConfigError(f"Duplicate SKU '{sku}' found in products.")
        skus.add(sku)

        variants = prod.get("variants", [])
        if not variants:
            raise ConfigError(f"Product '{sku}' must have at least one variant.")

        variant_labels = set()
        for var in variants:
            label = var.get("label")
            if label in variant_labels:
                raise ConfigError(
                    f"Duplicate variant label '{label}' in product SKU '{sku}'."
                )
            variant_labels.add(label)

    policies = data.get("policies", [])
    if not policies:
        raise ConfigError("Config must contain at least one policy.")

    sample_replies = data.get("sample_replies", [])
    if len(sample_replies) < 2 or len(sample_replies) > 6:
        raise ConfigError("Config must contain between 2 and 6 sample replies.")


def import_config(
    conn: sqlite3.Connection,
    data: dict[str, Any],
    *,
    replace: bool = False,
) -> int:
    """Import seller config into SQLite database.

    Runs inside a single transaction.

    Returns:
        The integer seller_id.
    """
    validate_config(data)

    shop = data["shop"]
    slug = shop["slug"]

    with conn:
        existing = get_seller_by_slug(conn, slug)
        if existing:
            if not replace:
                raise ConfigError(
                    f"Seller with slug '{slug}' already exists. Use replace=True to overwrite."
                )
            seller_id = existing["id"]
            conn.execute(
                """
                UPDATE sellers
                SET shop_name = ?, description = ?, tone = ?, default_language = ?, updated_at = datetime('now')
                WHERE id = ?;
                """,
                (
                    shop["name"],
                    shop.get("description", ""),
                    shop["tone"],
                    shop["default_language"],
                    seller_id,
                ),
            )
            # Remove existing products, languages, and config-sourced policies and samples
            # Preserves rows marked with source_type = 'seller_faq'
            conn.execute("DELETE FROM products WHERE seller_id = ?;", (seller_id,))
            conn.execute("DELETE FROM seller_languages WHERE seller_id = ?;", (seller_id,))
            conn.execute(
                "DELETE FROM policies WHERE seller_id = ? AND (source_type != 'seller_faq' OR source_type IS NULL);",
                (seller_id,),
            )
            conn.execute(
                "DELETE FROM sample_replies WHERE seller_id = ? AND (source_type != 'seller_faq' OR source_type IS NULL);",
                (seller_id,),
            )
        else:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO sellers (slug, shop_name, description, tone, default_language)
                VALUES (?, ?, ?, ?, ?);
                """,
                (
                    slug,
                    shop["name"],
                    shop.get("description", ""),
                    shop["tone"],
                    shop["default_language"],
                ),
            )
            seller_id = cur.lastrowid
            assert seller_id is not None

        for lang in shop["languages"]:
            conn.execute(
                "INSERT INTO seller_languages (seller_id, language) VALUES (?, ?);",
                (seller_id, lang),
            )

        cur = conn.cursor()
        for prod in data["products"]:
            attrs = json.dumps(prod.get("attributes") or {})
            cur.execute(
                """
                INSERT INTO products (
                    seller_id, sku, name, category, description,
                    attributes, stock_status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    seller_id,
                    prod["sku"],
                    prod["name"],
                    prod.get("category"),
                    prod.get("description"),
                    attrs,
                    prod["stock_status"],
                    prod.get("notes"),
                ),
            )
            product_id = cur.lastrowid
            assert product_id is not None

            for var in prod["variants"]:
                conn.execute(
                    """
                    INSERT INTO product_variants (product_id, label, price_inr)
                    VALUES (?, ?, ?);
                    """,
                    (product_id, var["label"], int(var["price_inr"])),
                )

        for pol in data["policies"]:
            conn.execute(
                """
                INSERT INTO policies (seller_id, topic, title, body, source_type)
                VALUES (?, ?, ?, ?, 'config')
                ON CONFLICT(seller_id, topic, title) DO UPDATE SET
                    body = excluded.body,
                    source_type = 'config';
                """,
                (seller_id, pol["topic"], pol["title"], pol["body"]),
            )

        for samp in data["sample_replies"]:
            conn.execute(
                """
                INSERT INTO sample_replies (seller_id, language, customer_message, reply, source_type)
                VALUES (?, ?, ?, ?, 'config');
                """,
                (seller_id, samp["language"], samp["customer_message"], samp["reply"]),
            )

        if is_fts5_available(conn):
            try:
                conn.execute("INSERT INTO products_fts(products_fts) VALUES('rebuild');")
            except Exception:
                pass

        return seller_id


def export_config(conn: sqlite3.Connection, slug: str) -> dict[str, Any]:
    """Export a seller from the database into the standard config JSON structure."""
    seller = get_seller_by_slug(conn, slug)
    if not seller:
        raise ConfigError(f"Seller with slug '{slug}' not found.")

    seller_id = seller["id"]

    # Languages
    cur = conn.cursor()
    cur.execute(
        "SELECT language FROM seller_languages WHERE seller_id = ? ORDER BY language ASC;",
        (seller_id,),
    )
    languages = [row["language"] for row in cur.fetchall()]

    shop_dict = {
        "slug": seller["slug"],
        "name": seller["shop_name"],
        "description": seller["description"] or "",
        "tone": seller["tone"],
        "default_language": seller["default_language"],
        "languages": languages,
    }

    # Products
    cur.execute(
        """
        SELECT id, sku, name, category, description, attributes, stock_status, notes
        FROM products WHERE seller_id = ? ORDER BY id ASC;
        """,
        (seller_id,),
    )
    product_rows = cur.fetchall()

    products = []
    for p in product_rows:
        pid = p["id"]
        cur.execute(
            "SELECT label, price_inr FROM product_variants WHERE product_id = ? ORDER BY id ASC;",
            (pid,),
        )
        variant_rows = cur.fetchall()
        variants = [
            {"label": v["label"], "price_inr": v["price_inr"]} for v in variant_rows
        ]

        attrs = {}
        if p["attributes"]:
            try:
                attrs = json.loads(p["attributes"])
            except json.JSONDecodeError:
                attrs = {}

        prod_dict: dict[str, Any] = {
            "sku": p["sku"],
            "name": p["name"],
            "stock_status": p["stock_status"],
            "variants": variants,
        }
        if p["category"]:
            prod_dict["category"] = p["category"]
        if p["description"]:
            prod_dict["description"] = p["description"]
        if attrs:
            prod_dict["attributes"] = attrs
        if p["notes"]:
            prod_dict["notes"] = p["notes"]

        products.append(prod_dict)

    # Policies
    cur.execute(
        "SELECT topic, title, body FROM policies WHERE seller_id = ? AND (source_type = 'config' OR source_type IS NULL) ORDER BY id ASC;",
        (seller_id,),
    )
    policies = [
        {"topic": row["topic"], "title": row["title"], "body": row["body"]}
        for row in cur.fetchall()
    ]

    # Sample replies
    cur.execute(
        """
        SELECT language, customer_message, reply
        FROM sample_replies WHERE seller_id = ? AND (source_type = 'config' OR source_type IS NULL) ORDER BY id ASC;
        """,
        (seller_id,),
    )
    sample_replies = [
        {
            "language": row["language"],
            "customer_message": row["customer_message"],
            "reply": row["reply"],
        }
        for row in cur.fetchall()
    ]

    exported: dict[str, Any] = {
        "schema_version": 1,
        "meta": {"exported": True},
        "shop": shop_dict,
        "products": products,
        "policies": policies,
        "sample_replies": sample_replies,
    }

    validate_config(exported)
    return exported


def parse_price_inr(raw: Any) -> int:
    """Sanitize and parse integer price in INR, stripping currency symbols, commas, and decimals."""
    if isinstance(raw, (int, float)):
        return int(round(raw))
    text = str(raw).strip()
    for prefix in ("₹", "rs.", "rs", "inr"):
        if text.lower().startswith(prefix):
            text = text[len(prefix):].strip()
    for suffix in ("/-", "rupees", "rs.", "rs", "inr"):
        if text.lower().endswith(suffix):
            text = text[:-len(suffix)].strip()
    text = text.replace(",", "").strip()
    if "." in text:
        text = text.split(".")[0].strip()
    return int(text)


def import_products_csv(conn: sqlite3.Connection, slug: str, csv_path: str) -> int:
    """Import products from CSV for an existing shop.

    Expected CSV header:
    sku,name,category,description,variant_label,price_inr,stock_status,sizes,colors,notes
    """
    seller = get_seller_by_slug(conn, slug)
    if not seller:
        raise ConfigError(f"Seller with slug '{slug}' not found.")

    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    seller_id = seller["id"]

    products_by_sku: dict[str, dict[str, Any]] = {}

    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sku = row["sku"].strip()
            if not sku:
                continue

            if sku not in products_by_sku:
                attrs: dict[str, list[str]] = {}
                if row.get("sizes"):
                    attrs["sizes"] = [s.strip() for s in row["sizes"].split(";") if s.strip()]
                if row.get("colors"):
                    attrs["colors"] = [c.strip() for c in row["colors"].split(";") if c.strip()]

                valid_statuses = {"in_stock", "low_stock", "out_of_stock", "made_to_order"}
                raw_status = (row.get("stock_status") or "in_stock").strip().lower().replace(" ", "_").replace("-", "_")
                status = raw_status if raw_status in valid_statuses else "in_stock"

                products_by_sku[sku] = {
                    "sku": sku,
                    "name": row["name"].strip(),
                    "category": row.get("category", "").strip() or None,
                    "description": row.get("description", "").strip() or None,
                    "stock_status": status,
                    "notes": row.get("notes", "").strip() or None,
                    "attributes": attrs,
                    "variants": [],
                }

            var_label = (row.get("variant_label") or "").strip() or "Standard"
            price_val = parse_price_inr(row.get("price_inr", "0"))

            products_by_sku[sku]["variants"].append(
                {
                    "label": var_label,
                    "price_inr": price_val,
                }
            )

    with conn:
        for p in products_by_sku.values():
            attrs_json = json.dumps(p["attributes"])
            cur = conn.cursor()
            # Upsert product
            cur.execute(
                """
                INSERT INTO products (
                    seller_id, sku, name, category, description,
                    attributes, stock_status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(seller_id, sku) DO UPDATE SET
                    name = excluded.name,
                    category = excluded.category,
                    description = excluded.description,
                    attributes = excluded.attributes,
                    stock_status = excluded.stock_status,
                    notes = excluded.notes;
                """,
                (
                    seller_id,
                    p["sku"],
                    p["name"],
                    p["category"],
                    p["description"],
                    attrs_json,
                    p["stock_status"],
                    p["notes"],
                ),
            )
            cur.execute(
                "SELECT id FROM products WHERE seller_id = ? AND sku = ?;",
                (seller_id, p["sku"]),
            )
            product_id = cur.fetchone()["id"]

            for var in p["variants"]:
                conn.execute(
                    """
                    INSERT INTO product_variants (product_id, label, price_inr)
                    VALUES (?, ?, ?)
                    ON CONFLICT(product_id, label) DO UPDATE SET
                        price_inr = excluded.price_inr;
                    """,
                    (product_id, var["label"], var["price_inr"]),
                )

    return len(products_by_sku)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m engine.importer <path-to-seller.json> [--replace]")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    replace_flag = "--replace" in sys.argv
    if not json_path.exists():
        print(f"Error: file not found at {json_path}")
        sys.exit(1)

    with json_path.open("r", encoding="utf-8") as file:
        config_data = json.load(file)

    connection = connect()
    try:
        sid = import_config(connection, config_data, replace=replace_flag)
        slug_name = config_data["shop"]["slug"]
        print(f"Successfully imported '{slug_name}' (seller_id={sid})")
    finally:
        connection.close()
