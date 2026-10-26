# Sovereign Agentic AI Workbench — Required Features & Tech Stack (Low-Cost Build)

**Goal:** Every feature below is required for the MVP. All tools chosen are free/open-source, so total software cost stays at **$0**. Hardware cost stays **$0–450** depending on what you already own.

---

## 1. Login & Access Control
**What it does (plain terms):** A simple username/password screen so only authorized people can open the workbench. No complicated multi-user permission system needed yet — just one admin account is enough for the demo.

**Tech to use:**
- FastAPI + `passlib` (bcrypt for password hashing) + `python-jose` (JWT tokens)
- Cost: $0 (all open-source Python libraries)

---

## 2. Model Manager (the "brain" you talk to)
**What it does:** Runs one AI language model directly on your own computer — nothing is sent to the internet. A dropdown lets you switch between models if you set up more than one.

**Tech to use:**
- **Ollama** — free tool that runs AI models locally
- **Qwen2.5-7B-Instruct** (quantized, Q4) — main model, good balance of smart answers and speed
- Backup lighter model for weaker computers: **Llama-3.2-3B** or **Phi-3.5-mini** (runs on CPU, no GPU needed)
- Cost: $0

---

## 3. Agent Orchestrator (the "decision maker")
**What it does:** Coordinates the whole process automatically: understands your question → looks up relevant documents → decides if a tool (like a calculator) is needed → writes a draft answer → double-checks the answer against the evidence before showing it to you.

**Tech to use:**
- **LangGraph** (or a simple hand-written Python state machine if you want fewer dependencies)
- Cost: $0

---

## 4. Document Intelligence (reading your files)
**What it does:** Lets you upload PDFs, Word docs, and scanned images/photos. If a document is a scanned image (not selectable text), it uses OCR to "read" the text out of the picture. Then it breaks the text into small chunks the AI can search through.

**Tech to use:**
- **Tesseract OCR** — free text-recognition engine for scanned pages/photos
- Basic Python text-splitting for chunking
- Cost: $0

---

## 5. RAG Knowledge Base (grounded, evidence-based answers)
**What it does:** Instead of the AI making things up, it searches your uploaded documents first and answers using real content from them — and shows you exactly which document/page the answer came from (a citation), so answers are trustworthy.

**Tech to use:**
- **ChromaDB** — free local vector database for document search
- **nomic-embed-text** (or `bge-small-en-v1.5`) — free embedding model that turns text into searchable data
- Cost: $0

---

## 6. Tool Execution Layer (giving the agent "hands")
**What it does:** Lets the AI actually *do* things, not just talk — e.g., run a calculation, search your documents directly, or generate a report file. This is what makes it an "agent" instead of a plain chatbot.

**Tech to use (pick 2–3 for the demo):**
- Calculator/data tool: Python **pandas** or **numexpr** (sandboxed)
- Document search tool: connects to the RAG system above
- Report generator tool: see item 9 below
- Cost: $0

---

## 7. Multimodal AI (understanding scanned/photographed documents)
**What it does:** Handles the "picture of a document" case — e.g., a scanned inspection report — so the AI can extract and reason over its content, not just plain typed text.

**Tech to use:**
- **Tesseract OCR** for most cases (cheap, fast)
- Optional upgrade for messy/handwritten scans: **Qwen2-VL-7B-Instruct**, a free local vision-capable model
- Cost: $0

---

## 8. Security & Governance (proving nothing leaves your computer)
**What it does:** Keeps the whole system running only on your local network — no calls out to the internet — and keeps a simple record of every request made, so you can prove exactly what happened and when.

**Tech to use:**
- Local-only network binding in the backend config
- Simple audit log table in a database, recording: timestamp, user, question asked, sources found, tools used, final answer
- **SQLite** (simplest, no extra setup) or **PostgreSQL** (if you want a "real" database)
- Verify with **Wireshark** or **netstat** (free network monitoring tools) that zero data goes out during a demo
- Cost: $0

---

## 9. Deliverable Generator (turning answers into real documents)
**What it does:** Packages the AI's findings into a proper, shareable report — like a maintenance recommendation — as a Word doc, PDF, or plain text file, complete with citations.

**Tech to use:**
- **python-docx** (Word files), **reportlab** (PDF files), or **Pandoc** (convert between formats)
- Cost: $0

---

## 10. Frontend Dashboard (what the user actually sees/clicks)
**What it does:** The web page where you log in, upload documents, chat with the AI, and view past requests/audit logs.

**Tech to use:**
- **React 18 + Next.js 14** (or plain React + Vite for something lighter/simpler)
- Cost: $0

---

## 11. Backend API (glue between frontend and AI)
**What it does:** Handles all requests between the web page and the AI system behind the scenes.

**Tech to use:**
- **Python 3.11 + FastAPI + Uvicorn**
- Cost: $0

---

## 12. Packaging & Setup (making it easy to run anywhere)
**What it does:** Lets the entire system start up with a single command on any computer, so it's easy to demo or hand off.

**Tech to use:**
- **Docker + Docker Compose** — one command (`docker compose up`) starts everything
- Cost: $0

---

## Hardware — What You Actually Need to Spend On

| Situation | What to do | Cost |
|---|---|---|
| You have a laptop/desktop with ≥16GB RAM and a GPU with ≥8GB VRAM (e.g. RTX 3060) | Just use it — runs the 7B model comfortably | **$0** |
| You have no GPU (integrated graphics only) | Use a smaller model (Llama-3.2-3B or Phi-3.5-mini) on CPU — slower but works for a scripted demo | **$0** |
| Your existing hardware is too slow | Buy a used RTX 3060 (12GB) as a one-time upgrade | **~$180–230** |
| Want extra headroom (e.g. for vision model too) | Used RTX 4060 Ti (16GB) | **~$300–430** |

**Avoid:** renting cloud GPUs for the actual demo — it undermines the whole "sovereign / offline" selling point. Cloud GPU rental (~$0.20–0.40/hr) is fine only for a few hours of *pre-demo testing*, not the live show.

---

## Total Cost Summary

| Category | Cost |
|---|---|
| All software (every tool above) | **$0** |
| Hardware, if you already own a decent PC | **$0** |
| Hardware, if a GPU upgrade is needed | **$180–450** |
| Optional cloud testing before the demo | **$0–10** |
| **Total project cost** | **$0 to ~$460** |
