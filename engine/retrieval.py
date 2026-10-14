"""Context retrieval and prompt block formatting for ReplyDesk."""

import json
import sqlite3
from dataclasses import dataclass
from typing import Any

from engine.guardrails import extract_amounts, script_of


@dataclass
class Context:
    shop: dict[str, Any]
    catalogue_block: str
    policies_block: str
    examples: list[dict[str, str]]
    known_amounts: set[int]


STOCK_STATUS_MAP = {
    "in_stock": "in stock",
    "low_stock": "low stock (limited)",
    "out_of_stock": "out of stock",
    "made_to_order": "made to order",
}


def build_context(
    conn: sqlite3.Connection,
    seller_id: int,
    message: str | None = None,
    *,
    max_products: int = 40,
) -> Context:
    """Build the context package for a given seller to feed the prompt.

    Puts the whole catalogue (up to max_products) into context.
    Collects all known prices and currency amounts from products and policies.
    """
    cur = conn.cursor()

    # 1. Shop details
    cur.execute(
        "SELECT id, slug, shop_name, description, tone, default_language "
        "FROM sellers WHERE id = ?;",
        (seller_id,),
    )
    seller_row = cur.fetchone()
    if not seller_row:
        raise ValueError(f"Seller with id {seller_id} not found.")

    cur.execute(
        "SELECT language FROM seller_languages WHERE seller_id = ? ORDER BY language ASC;",
        (seller_id,),
    )
    languages = [r["language"] for r in cur.fetchall()]

    shop = {
        "slug": seller_row["slug"],
        "name": seller_row["shop_name"],
        "description": seller_row["description"] or "",
        "tone": seller_row["tone"],
        "default_language": seller_row["default_language"],
        "languages": languages,
    }

    # 2. Products and variants
    cur.execute(
        """
        SELECT id, sku, name, category, description, attributes, stock_status, notes
        FROM products WHERE seller_id = ?
        ORDER BY id ASC
        LIMIT ?;
        """,
        (seller_id, max_products),
    )
    product_rows = cur.fetchall()

    known_amounts: set[int] = set()
    catalogue_lines: list[str] = []

    for p in product_rows:
        pid = p["id"]
        cur.execute(
            "SELECT label, price_inr FROM product_variants WHERE product_id = ? ORDER BY price_inr ASC;",
            (pid,),
        )
        variant_rows = cur.fetchall()
        for v in variant_rows:
            known_amounts.add(int(v["price_inr"]))

        # Build variants string
        # e.g. "500 g ₹650; 1 kg ₹1200"
        var_strs = [f"{v['label']} ₹{v['price_inr']}" for v in variant_rows]
        variants_summary = "; ".join(var_strs) if var_strs else "Price unavailable"

        # Category
        cat_str = f" ({p['category']})" if p["category"] else ""

        # Attributes
        attrs_str = ""
        if p["attributes"]:
            try:
                attrs_dict = json.loads(p["attributes"])
                attr_parts = []
                for k, val in attrs_dict.items():
                    if isinstance(val, list):
                        attr_parts.append(f"{k}: {', '.join(str(x) for x in val)}")
                    else:
                        attr_parts.append(f"{k}: {val}")
                if attr_parts:
                    attrs_str = " | " + " | ".join(attr_parts)
            except json.JSONDecodeError:
                pass

        # Stock status
        stock_text = STOCK_STATUS_MAP.get(p["stock_status"], p["stock_status"])

        # Line construction
        line = f"- [{p['sku']}] {p['name']}{cat_str}: {variants_summary}{attrs_str} | Stock: {stock_text}"
        if p["notes"]:
            line += f" | Notes: {p['notes']}"
            # Extract any amounts mentioned in notes
            for amt in extract_amounts(p["notes"]):
                known_amounts.add(amt)

        if p["description"]:
            for amt in extract_amounts(p["description"]):
                known_amounts.add(amt)

        catalogue_lines.append(line)

    catalogue_block = "\n".join(catalogue_lines)

    # 3. Policies
    cur.execute(
        "SELECT topic, title, body FROM policies WHERE seller_id = ? ORDER BY id ASC;",
        (seller_id,),
    )
    policy_rows = cur.fetchall()
    policy_lines: list[str] = []

    for pol in policy_rows:
        topic_upper = pol["topic"].upper()
        policy_lines.append(f"- {topic_upper} — {pol['title']}: {pol['body']}")
        for amt in extract_amounts(pol["body"]):
            known_amounts.add(amt)

    policies_block = "\n".join(policy_lines)

    # 4. Sample replies (few-shot)
    cur.execute(
        "SELECT language, customer_message, reply FROM sample_replies WHERE seller_id = ? ORDER BY id ASC;",
        (seller_id,),
    )
    all_samples = [
        {
            "language": r["language"],
            "customer_message": r["customer_message"],
            "reply": r["reply"],
        }
        for r in cur.fetchall()
    ]

    selected_samples: list[dict[str, str]] = []
    if message:
        msg_script = script_of(message)
        # Prioritize matching script
        matching = []
        others = []
        for s in all_samples:
            s_script = script_of(s["customer_message"])
            if s_script == msg_script:
                matching.append(s)
            else:
                others.append(s)
        selected_samples = (matching + others)[:3]
    else:
        selected_samples = all_samples[:3]

    return Context(
        shop=shop,
        catalogue_block=catalogue_block,
        policies_block=policies_block,
        examples=selected_samples,
        known_amounts=known_amounts,
    )
