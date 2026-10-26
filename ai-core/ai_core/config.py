"""AI-core settings (Person A). Read from environment variables / backend/.env."""
import os
from pathlib import Path

from dotenv import load_dotenv

AI_CORE_DIR = Path(__file__).resolve().parent.parent      # .../ai-core
ROOT_DIR = AI_CORE_DIR.parent                              # project root
BACKEND_DIR = ROOT_DIR / "backend"

# One shared .env for the whole project. Real environment variables win over the file.
load_dotenv(BACKEND_DIR / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR") or (BACKEND_DIR / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma"
REPORT_DIR = DATA_DIR / "reports"
for _d in (UPLOAD_DIR, CHROMA_DIR, REPORT_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _csv(name: str, default: str) -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b-instruct-q4_K_M")
AVAILABLE_MODELS = _csv("AVAILABLE_MODELS", LLM_MODEL)
if LLM_MODEL not in AVAILABLE_MODELS:
    AVAILABLE_MODELS.insert(0, LLM_MODEL)
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

# Optional vision-language model for messy scans/handwriting (leave empty to disable).
VISION_MODEL = os.getenv("VISION_MODEL", "").strip()
VISION_FALLBACK_MIN_CHARS = int(os.getenv("VISION_FALLBACK_MIN_CHARS", "40"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT_SECONDS", "120"))

TESSERACT_CMD = os.getenv("TESSERACT_CMD", "").strip()
TOP_K = int(os.getenv("TOP_K", "4"))

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
