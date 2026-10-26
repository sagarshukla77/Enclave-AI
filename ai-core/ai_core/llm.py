"""Thin client for the local Ollama server. Nothing here leaves localhost."""
import base64
import io

import requests

from . import config


class OllamaError(RuntimeError):
    """Raised when Ollama is unreachable or returns an error."""


def _post(path: str, payload: dict) -> dict:
    try:
        r = requests.post(f"{config.OLLAMA_URL}{path}", json=payload, timeout=config.LLM_TIMEOUT)
    except requests.exceptions.ConnectionError:
        raise OllamaError(
            f"Cannot reach Ollama at {config.OLLAMA_URL}. Is it running? (try: ollama serve)"
        )
    except requests.exceptions.Timeout:
        raise OllamaError("Ollama took too long to respond. Try a smaller model.")
    if r.status_code != 200:
        raise OllamaError(f"Ollama error {r.status_code}: {r.text[:300]}")
    return r.json()


def generate(prompt: str, model: str | None = None, system: str | None = None,
             json_mode: bool = False, temperature: float = 0.1) -> str:
    payload = {
        "model": model or config.LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system
    if json_mode:
        payload["format"] = "json"
    return _post("/api/generate", payload).get("response", "").strip()


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts with the local embedding model."""
    if not texts:
        return []
    data = _post("/api/embed", {"model": config.EMBED_MODEL, "input": texts})
    vectors = data.get("embeddings")
    if not vectors or len(vectors) != len(texts):
        raise OllamaError("Embedding model returned an unexpected response.")
    return vectors


def list_local_models() -> list[str]:
    try:
        r = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def is_up() -> bool:
    try:
        return requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=3).status_code == 200
    except Exception:
        return False


def describe_image(image, prompt: str | None = None, model: str | None = None) -> str:
    """Ask the local vision-language model to read a PIL image (multimodal path)."""
    model = model or config.VISION_MODEL
    if not model:
        raise OllamaError("No VISION_MODEL configured in .env.")
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    payload = {
        "model": model, "stream": False, "options": {"temperature": 0},
        "prompt": prompt or ("Transcribe all text in this scanned document exactly as written, "
                             "including tables, numbers and units. Output only the text."),
        "images": [base64.b64encode(buf.getvalue()).decode()],
    }
    return _post("/api/generate", payload).get("response", "").strip()


def model_status() -> dict:
    """Which of the configured models are actually pulled in Ollama?"""
    installed = list_local_models()

    def have(name: str) -> bool:
        return bool(name) and any(i == name or i == f"{name}:latest" for i in installed)

    return {
        "ollama_up": is_up(), "installed": installed,
        "llm": {"name": config.LLM_MODEL, "installed": have(config.LLM_MODEL)},
        "embedding": {"name": config.EMBED_MODEL, "installed": have(config.EMBED_MODEL)},
        "vision": {"name": config.VISION_MODEL or None, "enabled": bool(config.VISION_MODEL),
                   "installed": have(config.VISION_MODEL)},
        "available_models": [{"name": m, "installed": have(m)} for m in config.AVAILABLE_MODELS],
    }
