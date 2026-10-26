"""Document intelligence: text extraction (typed + OCR) and chunking.

Every extractor returns a list of pages: {"page": int, "text": str, "method": "text" | "ocr"}
so that later steps can cite "file.pdf, page 3".
"""
from pathlib import Path

import pdfplumber
import pytesseract
from docx import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from PIL import Image, ImageOps

from . import config, llm

if config.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD

MIN_TEXT_CHARS = 25          # a PDF page with less text than this is treated as a scan
OCR_RESOLUTION = 250         # dpi used when rasterising scanned PDF pages


def _prep(image: Image.Image) -> Image.Image:
    img = ImageOps.exif_transpose(image).convert("L")      # fix phone-photo rotation, grayscale
    img = ImageOps.autocontrast(img)
    if max(img.size) < 1500:                                # tiny scans read badly - upscale
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
    return img


def _tesseract(image: Image.Image) -> tuple[str, str | None]:
    try:
        return pytesseract.image_to_string(_prep(image), config="--psm 6").strip(), None
    except pytesseract.TesseractNotFoundError:
        return "", ("Tesseract OCR is not installed or not on PATH. Install it (see README) "
                    "or set TESSERACT_CMD in .env.")


def read_image(image: Image.Image, force_vision: bool = False) -> tuple[str, str, list[str]]:
    """Read text from an image. Returns (text, method, warnings); method = 'ocr' or 'vision'.

    Tesseract is the safety net: if the vision model is requested but fails or returns nothing,
    we fall back to Tesseract instead of returning empty text.
    """
    warnings: list[str] = []
    if force_vision and not config.VISION_MODEL:
        warnings.append("use_vision was requested but VISION_MODEL is not set in .env; used Tesseract instead.")
        force_vision = False

    if force_vision:                                         # vision first, Tesseract as fallback
        try:
            vtext = llm.describe_image(image)
            if vtext:
                return vtext, "vision", warnings
            warnings.append("Vision model returned no text; fell back to Tesseract.")
        except llm.OllamaError as e:
            warnings.append(f"Vision model failed ({e}); fell back to Tesseract.")

    text, tess_error = _tesseract(image)
    if config.VISION_MODEL and not force_vision and (tess_error or len(text) < config.VISION_FALLBACK_MIN_CHARS):
        try:                                                 # Tesseract found little -> try vision
            vtext = llm.describe_image(image)
            if len(vtext) > len(text):
                return vtext, "vision", warnings
        except llm.OllamaError as e:
            warnings.append(f"Vision model failed: {e}")
    if tess_error:
        warnings.append(tess_error)
    return text, "ocr", warnings


def extract_pdf(path: Path, force_vision: bool = False) -> tuple[list[dict], list[str]]:
    pages, warnings = [], []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            method = "text"
            if len(text) < MIN_TEXT_CHARS or force_vision:   # scanned page -> OCR / vision
                text, method, warns = read_image(page.to_image(resolution=OCR_RESOLUTION).original, force_vision)
                warnings += [f"Page {i}: {w}" for w in warns]
            pages.append({"page": i, "text": text, "method": method})
    return pages, warnings


def extract_docx(path: Path) -> tuple[list[dict], list[str]]:
    doc = Document(path)
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:                                # inspection sheets are often tables
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    return [{"page": 1, "text": "\n".join(parts), "method": "text"}], []


def extract_image(path: Path, force_vision: bool = False) -> tuple[list[dict], list[str]]:
    with Image.open(path) as img:
        text, method, warnings = read_image(img, force_vision)
    return [{"page": 1, "text": text, "method": method}], warnings


def extract_pages(path: Path, force_vision: bool = False) -> tuple[list[dict], list[str]]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_pdf(path, force_vision)
    if ext == ".docx":
        return extract_docx(path)
    if ext in config.IMAGE_EXTENSIONS:
        return extract_image(path, force_vision)
    raise ValueError(f"Unsupported file type '{ext}'")


def chunk_pages(pages: list[dict], source: str, chunk_size: int = 500,
                chunk_overlap: int = 50) -> list[dict]:
    """Split each page into overlapping chunks, keeping filename + page for citations."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = []
    for page in pages:
        for piece in splitter.split_text(page["text"]):
            if piece.strip():
                chunks.append({
                    "id": f"{source}::p{page['page']}::c{len(chunks)}",
                    "text": piece,
                    "source": source,
                    "page": page["page"],
                    "chunk_index": len(chunks),
                })
    return chunks
