# Seller config format

A shop is described by one JSON file. It is the import/export format; the runtime source of truth is SQLite (see `DBMS.md`). The machine-readable definition is `config/seller.schema.json` (JSON Schema, draft 2020-12). Validate with `jsonschema` before importing.

## Top-level structure

```json
{
  "schema_version": 1,
  "meta": { "fictional_sample": true },
  "shop": { ... },
  "products": [ ... ],
  "policies": [ ... ],
  "sample_replies": [ ... ]
}
```

## `shop`

| Field | Type | Required | Notes |
|---|---|---|---|
| `slug` | string | yes | Lowercase letters, digits, underscores. Unique per installation. Example: `urban_thread` |
| `name` | string | yes | Shop name shown to customers |
| `description` | string | no | One or two sentences about the shop |
| `tone` | string | yes | Free text, e.g. "friendly, short, uses 'ji'" |
| `default_language` | enum | yes | `en`, `hi`, `mr`, `hinglish` |
| `languages` | array of enum | yes | At least one; must include `default_language` |

Language codes: `en` English, `hi` Hindi (Devanagari), `mr` Marathi (Devanagari), `hinglish` Hindi in Latin letters.

## `products[]`

| Field | Type | Required | Notes |
|---|---|---|---|
| `sku` | string | yes | Unique within the shop |
| `name` | string | yes | |
| `category` | string | no | |
| `description` | string | no | Short, customer-facing facts only |
| `attributes` | object | no | Free-form: e.g. `sizes` and `colors` arrays, or `flavours`. Printed into the prompt |
| `stock_status` | enum | yes | `in_stock`, `low_stock`, `out_of_stock`, `made_to_order` |
| `notes` | string | no | Anything the model may state: lead time, ingredients, allergens |
| `variants` | array | yes (min 1) | Priced options |

`variants[]`: `label` (string, e.g. "500 g", "Standard"), `price_inr` (integer >= 0, whole rupees).

Only put facts you want the assistant to state. If it is not written here, the assistant must say the shop will check.

## `policies[]`

| Field | Type | Required | Notes |
|---|---|---|---|
| `topic` | enum | yes | `delivery`, `returns`, `payment`, `hours`, `ordering`, `other` |
| `title` | string | yes | Short heading |
| `body` | string | yes | The rule in plain language, with exact numbers (days, rupees) |

## `sample_replies[]`

2 to 6 examples of how this seller writes. Used as few-shot examples.

| Field | Type | Required |
|---|---|---|
| `language` | enum | yes |
| `customer_message` | string | yes |
| `reply` | string | yes |

Sample replies must not duplicate test messages in `eval/questions.json`, or the eval results would be inflated.

## CSV import for products

Columns (header row required):

```
sku,name,category,description,variant_label,price_inr,stock_status,sizes,colors,notes
```

- One row per priced variant. Repeat `sku`, `name`, and the other product columns for each variant of the same product; the first row wins if they differ.
- `sizes` and `colors` are semicolon-separated (`S;M;L`), stored in `attributes`.
- `stock_status` must be one of the four allowed values.
- `price_inr` is a whole number of rupees without symbols or commas.

## Mapping to the database

| Config | Table |
|---|---|
| `shop` | `sellers` and `seller_languages` |
| `products[]` | `products` (with `attributes` as JSON text) |
| `products[].variants[]` | `product_variants` |
| `policies[]` | `policies` |
| `sample_replies[]` | `sample_replies` |

`meta` and `schema_version` are not stored in tables. Export writes `schema_version: 1` and preserves nothing in `meta` unless the importer is extended to do so.

## Validation rules beyond the JSON schema

- `default_language` is in `languages`.
- SKUs are unique within the shop.
- Variant labels are unique within a product.
- Every shop has at least one product and at least one policy before drafting is allowed (the UI blocks drafting otherwise).

## Sample shops

Three fictional shops are provided for testing, each with a different tone and language mix:

| File | Shop | Type |
|---|---|---|
| `config/urban_thread.json` | Urban Thread | Women's kurtis and basics |
| `config/sweet_crumbs.json` | Sweet Crumbs | Home bakery |
| `config/kalakruti_jewels.json` | Kalakruti Jewels | Handmade and oxidised jewellery |

They are invented for testing and do not describe real businesses.
