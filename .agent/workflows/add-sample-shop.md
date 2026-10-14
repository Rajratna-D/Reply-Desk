# Workflow: add-sample-shop

Add or edit a shop config.

1. Ask the user for: shop name, what it sells, tone, languages, products with variants and prices, stock status, policies (delivery, returns, payment, hours, ordering), and 2 to 6 sample replies in the seller's style.
2. Write `config/<slug>.json` following `docs/CONFIG_SCHEMA.md`.
3. Validate against `config/seller.schema.json` and check: `default_language` is in `languages`, SKUs are unique, variant labels are unique within a product.
4. Import it with `python -m engine.importer config/<slug>.json` and print the catalogue to confirm.
5. Make sure no sample reply duplicates a message in `eval/questions.json`.
6. If it is a real seller's data, remove customer names and phone numbers, and keep only what the seller agreed to share.
