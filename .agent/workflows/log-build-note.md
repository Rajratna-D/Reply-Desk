# Workflow: log-build-note

Append a dated line to `docs/BUILD_LOG.md`.

Format: `YYYY-MM-DD HH:MM IST — [type] note`, where type is `decision`, `bug`, `fix`, `measurement`, `user`, or `note`.

- Record only what actually happened. No estimated or invented numbers.
- For measurements include the model tag, the hardware, and how it was measured.
- For user feedback include only what the person actually said, with their permission.
