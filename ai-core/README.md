# ai-core (Person A)
Python package `ai_core`. It has no web code; the backend imports it through `backend/app/agent_interface.py`.

| Module | Job |
|---|---|
| `llm.py` | Ollama client: generate, embed, vision, model status |
| `ingestion.py` | PDF/DOCX/image text extraction, Tesseract OCR (+ optional vision model), chunking with page numbers |
| `rag.py` | embeddings stored in ChromaDB, top-k retrieval with filename + page |
| `tools.py` | safe calculator + document search |
| `agent.py` | LangGraph flow: classify -> retrieve -> calculate (if needed) -> draft -> validate |
| `config.py` | settings from `backend/.env` |
