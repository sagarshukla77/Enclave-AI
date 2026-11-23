"""Bridge between the backend (Person B) and the AI core (Person A, in ../ai-core).

main.py only talks to the AI core through this file.
Set MOCK_AGENT=true in .env to get the old mock answer (handy for frontend work without Ollama).
"""
import os
import sys
from pathlib import Path

# ai-core/ is a sibling folder of backend/, so add it to the import path.
_AI_CORE_DIR = Path(__file__).resolve().parents[2] / "ai-core"
if str(_AI_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_CORE_DIR))

from ai_core import agent as _agent          # noqa: E402
from ai_core import config as ai_config      # noqa: E402,F401
from ai_core import ingestion, llm, rag, tools   # noqa: E402,F401
from ai_core.llm import OllamaError          # noqa: E402,F401


def _mock_enabled() -> bool:
    return os.getenv("MOCK_AGENT", "").strip().lower() in {"1", "true", "yes"}


def resolve_model(requested):
    """Pick the model to use. Unknown names (e.g. Swagger's placeholder "string") fall back to the default."""
    if requested and requested in ai_config.AVAILABLE_MODELS:
        return requested, None
    if requested and requested.strip():
        return ai_config.LLM_MODEL, (
            f"Unknown model '{requested}', used the default '{ai_config.LLM_MODEL}'. "
            f"Available: {ai_config.AVAILABLE_MODELS}")
    return ai_config.LLM_MODEL, None


def run_agent(question, user, model=None):
    model_used, warning = resolve_model(model)

    if _mock_enabled():
        return {"answer": f"Mock response for: {question}", "sources": [], "tools_used": [],
                "user": user, "model": model_used}

    state = _agent.run_agent(question, model_used)
    result = {
        "answer": state["answer"],
        "sources": state["citations"],            # [{label, source, page, score, text}]
        "tools_used": state["tools_called"],      # [{tool, input, output}]
        "user": user,
        "model": model_used,
        "task_type": state.get("task_type"),
        "validation": state["validation"],
        "trace": state["trace"],
        "duration_seconds": state["duration_seconds"],
    }
    if warning:
        result["model_warning"] = warning
    return result
