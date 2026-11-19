Science Tutor Q&A Generator
===========================

This project bootstraps a synthetic data pipeline for a “science tutor” that creates multi-turn Q&A with hints and misconception correction across Physics, Biology, and Chemistry, and can be fine-tuned into a small model later (e.g., Qwen1.5-1.8B, LLaMA-3-1B) using LoRA/QLoRA.

What’s here (MVP)
-----------------
- Prompt templates for four agents: creator (question + gold), critic (quality gate), misconception generator, fixer tutor (guided correction).
- A minimal Python pipeline (`src/generate_dataset.py`) to orchestrate the agents, stream JSONL rows, and optionally run in dry-run mode without an API key.
- Schema and metadata tags to support evaluation splits (subject/level/topic/difficulty/cognitive dimension/misconception type).

Quickstart
----------
1) Install deps (Python 3.9+):
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2) Configure LLM endpoint (auto-loads `.env` at repo root). Priority: Hugging Face → Ollama → Qwen → OpenAI-compatible.
- Hugging Face Inference/Router (OpenAI-compatible API):
  ```
  HUGGINGFACE_API_TOKEN=hf_...
  HUGGINGFACE_ROUTER_MODEL=meta-llama/Llama-3.1-8B-Instruct   # example
  HUGGINGFACE_BASE_URL=https://router.huggingface.co   # adjust if HF changes URL
  ```
- Ollama local:
  ```
  OLLAMA_HOST=http://localhost:11434
  LOCAL_MODEL=deepseek-coder      # or your installed model
  ```
- Qwen (dashscope compatible):
  ```
  QWEN_API_KEY=sk-...
  QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
  QWEN_MODEL=qwen-max
  ```
- OpenAI-compatible:
  ```
  OPENAI_API_KEY=sk-...
  OPENAI_BASE_URL=https://api.openai.com/v1
  OPENAI_MODEL=gpt-4o-mini
  ```
Optional: `DRY_RUN=1` to skip API calls and emit stub data.

3) Generate a small shard:
```
python src\generate_dataset.py --subject physics --level high_school --topic "Newton's second law" --count 3 --out data\sample.jsonl
```

Outputs: JSONL rows with fields: subject, level, topic, question, gold_answer, difficulty, cognitive_dim, item_type, scenario, turns (teacher/student), misconceptions, critic scores.

4) Quick sanity summary of a generated file:
```
python src\evaluate_stub.py --data data\sample.jsonl
```

Project structure
-----------------
- `src/generate_dataset.py` — orchestrates multi-agent prompts, streams JSONL.
- `src/llm.py` — lightweight OpenAI-compatible client with dry-run mode.
- `src/schemas.py` — dataclasses for metadata rows.
- `src/evaluate_stub.py` — tiny summary script for pass rates and notes.
- `prompts/creator.md` — question + gold + reasoning + hints.
- `prompts/critic.md` — correctness/clarity/difficulty coverage gate.
- `prompts/misconception.md` — plausible wrong answers + tags.
- `prompts/fixer.md` — guided dialogue to correct a misconception.
- `requirements.txt` — only `openai` dependency to keep it minimal.

Next steps (suggested)
----------------------
- Expand prompt coverage per subject/level with concrete syllabus bullets.
- Add vector retrieval (concept cards/formulas) and plug it into the creator prompt context.
- Add evaluation harness: automatic rubric scores + human spot-check script.
- Fine-tune small model with LoRA/QLoRA; log results per subject/difficulty.
