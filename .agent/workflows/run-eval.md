# Workflow: run-eval

Run the evaluation and summarize it honestly.

1. Confirm Ollama is running and the model tag exists (`ollama list`).
2. Ask the user which model tag to evaluate and whether to include the `test` split (default: `dev` only while tuning).
3. Run `python -m eval.run_eval --model <tag> --notes "<short note>"`.
4. Read the generated markdown report in `eval/results/`.
5. List every failing case with the message, the reply, and a diagnosis: prompt problem, data problem, guardrail gap, or model-size limit.
6. Append a dated `measurement` line to `docs/BUILD_LOG.md` with the model tag, counts (for example `21/25`), and median latency.
7. Do not change the eval questions or scoring to improve results. Propose prompt or guardrail fixes instead and wait for the user's go-ahead.
