# Rule: local only

- The app may call only the local Ollama server (`OLLAMA_HOST`).
- Do not add cloud LLM APIs, analytics, telemetry, or runtime CDN assets.
- Do not send seller data or customer messages to any external service, including in tests.
- Run Streamlit bound to localhost: `streamlit run app.py --server.address localhost`.
- If a task seems to need a network call, stop and ask the user.
