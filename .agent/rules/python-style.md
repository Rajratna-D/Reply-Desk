# Rule: Python style

- Python 3.11+. Type hints on public functions. Small functions.
- SQL is always parameterized. Never build SQL with f-strings or `%` formatting.
- Open connections with `engine.db.connect` so `PRAGMA foreign_keys = ON` is always set.
- Use `with conn:` for transactions.
- Read settings from `engine/config.py`; never hardcode the model name, host, or paths.
- Write tests with pytest. Tests that need Ollama must be skipped automatically when it is not running.
- Ask before adding a dependency or changing `db/schema.sql` or the config format.
- Keep UI pages thin; put logic in `engine/`.
