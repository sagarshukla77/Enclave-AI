"""Checks that everything the backend needs is installed. Run (from backend/):  python check_setup.py"""
import shutil
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ai-core"))
ok = True


def line(good: bool, msg: str, fix: str = ""):
    global ok
    ok = ok and good
    print(("  [OK]   " if good else "  [FAIL] ") + msg + ("" if good or not fix else f"\n         -> {fix}"))


print(f"Python {sys.version.split()[0]}")
line(sys.version_info[:2] == (3, 11), "Python 3.11", "Python 3.11.x is recommended (3.10-3.12 usually also work)")

for mod in ["fastapi", "uvicorn", "multipart", "pdfplumber", "docx", "pytesseract", "PIL", "chromadb",
            "langgraph", "langchain_text_splitters", "numexpr", "passlib", "bcrypt", "jose",
            "reportlab", "dotenv", "requests"]:
    try:
        __import__(mod)
        line(True, f"python package: {mod}")
    except ImportError:
        line(False, f"python package: {mod}", "pip install -r requirements.txt")

try:
    import bcrypt
    ver = getattr(bcrypt, "__version__", "0")
    line(ver.startswith("4.0."), f"bcrypt {ver} (must be 4.0.x for passlib)", "pip install bcrypt==4.0.1")
except ImportError:
    pass

from ai_core import config  # noqa: E402

line((Path(__file__).resolve().parent / ".env").exists(), ".env file present", "copy .env.example to .env")
tess = config.TESSERACT_CMD or shutil.which("tesseract")
line(bool(tess) and (not config.TESSERACT_CMD or Path(config.TESSERACT_CMD).exists()),
     f"Tesseract OCR ({tess})" if tess else "Tesseract OCR",
     "Install Tesseract and/or set TESSERACT_CMD in .env")

try:
    names = [m["name"] for m in requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=4).json().get("models", [])]
    line(True, f"Ollama running at {config.OLLAMA_URL}")
    have = lambda n: n in names or f"{n}:latest" in names
    line(have(config.LLM_MODEL), f"LLM model '{config.LLM_MODEL}' pulled", f"ollama pull {config.LLM_MODEL}")
    line(have(config.EMBED_MODEL), f"embedding model '{config.EMBED_MODEL}' pulled", f"ollama pull {config.EMBED_MODEL}")
    if config.VISION_MODEL:
        if have(config.VISION_MODEL):
            print(f"  [OK]   vision model '{config.VISION_MODEL}' pulled (optional)")
        else:
            print(f"  [--]   vision model '{config.VISION_MODEL}' not pulled (optional; Tesseract is used)")
    else:
        print("  [--]   vision model not configured (optional; Tesseract is used)")
except Exception:
    line(False, f"Ollama running at {config.OLLAMA_URL}", "Open the Ollama app, or run: ollama serve")

print("\nAll good - start the API with:  python run.py" if ok else "\nFix the [FAIL] items above, then run this again.")
