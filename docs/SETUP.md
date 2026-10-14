# Setup

## Target hardware (developer laptop)

- CPU: Intel Core i5, 12th generation
- GPU: NVIDIA RTX 3050 Laptop, 6 GB VRAM
- RAM: not recorded yet. Add it here: `___ GB`
- OS: not recorded yet. Add it here: `___`

The 6 GB of VRAM is the main constraint. Keep the model and context small enough to run mostly on the GPU.

## Install

1. Python 3.11 or newer.
2. Ollama from https://ollama.com (check `ollama --version`; update if a model tag is not found).
3. NVIDIA driver up to date (so Ollama can use the GPU).
4. In the project folder:
   ```
   python -m venv .venv
   # Windows: .venv\Scripts\activate    Mac/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```

## Choosing the model

Gemma 4 comes in several sizes. Sources disagreed on exact VRAM needs and on the exact Ollama tag names (for example `e2b` / `e4b` versus `4b`), so verify before relying on this:

1. Open the Gemma 4 page in the Ollama library and note the real tags and download sizes.
2. Start with the smallest edge model (E2B). Then try the next size up (E4B) and compare.
3. A 12B model needs more than 6 GB at 4-bit quantization before the context window is counted, so expect it to spill into system RAM and run slowly on this laptop. Test before deciding.

Check where a model actually runs:
```
ollama pull <tag>
ollama run <tag> "Say hello in Marathi"
ollama ps        # shows how much is on GPU vs CPU
```
If `ollama ps` shows mostly GPU and replies arrive in a few seconds, the model is suitable. If it shows a large CPU share, try a smaller tag or a smaller context size.

Model names used by the app are set via environment variables, never in code:
```
MODEL_NAME=<tag you verified>
OLLAMA_HOST=http://localhost:11434
NUM_CTX=4096
```

## Verify the GPU is used

- Windows: Task Manager > Performance > GPU (look at dedicated GPU memory while generating)
- Any OS with NVIDIA tools: `nvidia-smi`

## Offline check (for the write-up)

After the model is downloaded, disable Wi-Fi and confirm the app still drafts replies. Note the result in `docs/BUILD_LOG.md`.

## Antigravity IDE notes

- Project instructions are in `AGENTS.md` (cross-tool). If you want Antigravity-specific overrides, a `GEMINI.md` takes precedence over `AGENTS.md`.
- Modular rules are in `.agent/rules/` and reusable workflows in `.agent/workflows/`. Some guides say newer Antigravity versions read from `.agents/` instead. If your version does not pick up the rules, rename the folder and check.
- Antigravity has a usage quota during preview. Keep the repo tidy (use `.gitignore`) so the agent does not waste tokens on junk.
- Suggested first prompt to the agent: "Read AGENTS.md and every file in docs/. Summarize the project in 10 lines, list any ambiguities, and propose a plan for Milestone 1 only. Do not write code yet."

## Environment file

Create `.env` (not committed):
```
MODEL_NAME=
OLLAMA_HOST=http://localhost:11434
NUM_CTX=4096
DB_PATH=data/replydesk.db
```

## .gitignore (minimum)

```
.venv/
__pycache__/
.env
data/
eval/results/
*.db
```
