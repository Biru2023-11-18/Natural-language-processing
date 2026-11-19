import os
from pathlib import Path
from typing import List, Dict, Tuple

from dotenv import load_dotenv

# Auto-load .env from project root if present
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class LLMClient:
    """
    Thin wrapper around chat completion providers. Order: Hugging Face, Ollama, Qwen, OpenAI-compatible.
    Respects DRY_RUN env to avoid network calls during wiring/tests.
    """

    def __init__(self, model: str | None = None):
        self.dry_run = os.getenv("DRY_RUN", "").lower() in {"1", "true", "yes"}
        self._client = None
        self._hf_client = None
        self.provider, self.api_key, self.base_url, resolved_model = self._resolve_provider()
        self.model = model or resolved_model

        if self.dry_run:
            return

        if self.provider == "hf":
            try:
                from huggingface_hub import InferenceClient

                self._hf_client = InferenceClient(
                    token=self.api_key,
                    base_url=self.base_url,
                )
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(
                    "Hugging Face client initialization failed. "
                    "Install deps and set HUGGINGFACE_API_TOKEN/HUGGINGFACE_ROUTER_MODEL."
                ) from exc
        else:
            try:
                from openai import OpenAI

                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(
                    "OpenAI-compatible client initialization failed. "
                    "Install deps and set provider keys/URLs in .env."
                ) from exc

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 512, temperature: float = 0.3) -> str:
        """
        Send chat messages; returns response text. In dry-run, returns a stub for quick validation.
        """
        if self.dry_run:
            content_preview = " | ".join(m["content"][:60] for m in messages[-3:])
            return f"[dry-run stub for {self.model}] {content_preview}"

        if self.provider == "hf":
            if not self._hf_client:
                raise RuntimeError("Hugging Face client not initialized.")
            return self._chat_hf(messages, max_tokens=max_tokens, temperature=temperature)

        if not self._client:
            raise RuntimeError("LLM client not initialized.")

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()

    def _chat_hf(self, messages: List[Dict[str, str]], max_tokens: int, temperature: float) -> str:
        """
        Use huggingface_hub's chat_completion for OpenAI-compatible routers.
        """
        output = self._hf_client.chat_completion(
            messages=messages,
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=False,
        )
        # huggingface_hub returns OpenAI-like structure
        if hasattr(output, "choices"):
            return output.choices[0].message["content"].strip()
        if isinstance(output, dict) and output.get("choices"):
            return output["choices"][0]["message"]["content"].strip()
        return str(output)

    def _resolve_provider(self) -> Tuple[str, str, str, str]:
        """
        Resolve provider credentials in priority order:
        1) Hugging Face Inference/Router (OpenAI-compatible) with HUGGINGFACE_API_TOKEN
        2) Ollama (LOCAL_MODEL + OLLAMA_HOST, OpenAI-compatible endpoint)
        3) Qwen compatible mode (QWEN_API_KEY + optional QWEN_BASE_URL)
        4) OpenAI-compatible defaults (OPENAI_API_KEY + OPENAI_BASE_URL)
        """
        # 1) Hugging Face Inference/Router (OpenAI-compatible)
        hf_token = os.getenv("HUGGINGFACE_API_TOKEN")
        hf_model = os.getenv("HUGGINGFACE_ROUTER_MODEL") or os.getenv("HUGGINGFACE_MODEL")
        hf_url = os.getenv("HUGGINGFACE_BASE_URL") or os.getenv("HUGGINGFACE_MODEL_URL")
        if hf_token and (hf_model or hf_url):
            base_url = hf_url or "https://router.huggingface.co"
            model = hf_model or "gpt2"
            return "hf", hf_token, base_url, model

        # 2) Ollama local (no real API key needed)
        ollama_host = os.getenv("OLLAMA_HOST")
        local_model = os.getenv("OPENAI_MODEL") or os.getenv("LOCAL_MODEL")
        if ollama_host and local_model:
            base_url = ollama_host.rstrip("/")
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            api_key = os.getenv("OLLAMA_API_KEY", "ollama")
            return "ollama", api_key, base_url, local_model

        # 3) Qwen compatible-mode endpoint
        qwen_key = os.getenv("QWEN_API_KEY")
        if qwen_key:
            base_url = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            model = os.getenv("OPENAI_MODEL") or os.getenv("QWEN_MODEL") or "qwen-max"
            return "qwen", qwen_key, base_url, model

        # 4) Generic OpenAI-compatible
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if not api_key:
            raise RuntimeError(
                "No provider credentials found. Add either OLLAMA_HOST+LOCAL_MODEL, "
                "QWEN_API_KEY (dashscope compatible), or OPENAI_API_KEY to your .env."
            )
        return "openai", api_key, base_url, model
