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

Verified for this setup:
- Tag: `gemma2:2b` (Google Gemma 2, 2B parameters)
- Download size: 1.6 GB
- VRAM footprint in Ollama: 1.9 GB (leaves >3 GB free on the 6 GB RTX 3050)
- `ollama ps` measurement: `100% GPU`, `NUM_CTX=4096`
- Measured inference speed: ~68.7 tokens/second (eval time), median reply latency ~3.5s

Model names used by the app are set via environment variables, never in code:
```
MODEL_NAME=gemma2:2b
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
