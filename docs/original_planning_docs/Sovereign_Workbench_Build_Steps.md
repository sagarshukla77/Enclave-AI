# Sovereign Agentic AI Workbench — Step-by-Step Build Guide

**What this is:** A plain-language, week-by-week walkthrough for building the project, with the exact tools/commands you'll use at each step. Follow it top to bottom, in order — each week builds on the one before it.

---

## Week 1 — Get the Basics Running on Your Computer

**In simple terms:** Before building anything fancy, you need the "engine" (an AI model) running on your own machine, and a skeleton web server ready to talk to it.

### Step 1.1 — Install Docker ✅ Already done
Docker lets you package your whole project so it runs the same way on any computer with one command. You don't need to touch this again until Week 7, when you'll write the `docker-compose.yml` file that starts everything together.
- Quick sanity check before moving on: run `docker --version` and `docker compose version` in your terminal — both should print a version number without errors. If either fails, fix that before continuing, since Week 7 depends on it.

### Step 1.2 — Install Ollama and download a model ✅ Already done
You've pulled your model already. Two things worth confirming right now, since everything later depends on this working smoothly:

- **Confirm the model actually runs and responds well.** Run:
  ```
  ollama run qwen2.5:7b-instruct-q4_K_M
  ```
  (swap in whatever model you actually pulled) and ask it 2-3 test questions. Pay attention to **how fast it responds** — this tells you whether your hardware can hit the "under 30 seconds per query" target from the PRD. If it's noticeably slow (many seconds just to start generating), pull a smaller backup model now rather than discovering the problem in Week 4:
  ```
  ollama pull llama3.2:3b-instruct-q4_K_M
  ```
- **Confirm Ollama is running as a background service**, not just a one-off terminal session. On most installs, Ollama runs automatically as a local server on port `11434`. Check this by running:
  ```
  curl http://localhost:11434/api/tags
  ```
  This should return a JSON list of your downloaded models. If it works, your backend (built below) will be able to talk to Ollama over this same local address — this is the exact connection point your FastAPI code will use.

### Step 1.3 — Decide your demo scenario now
This is a decision, not a coding step, but it's the most consequential thing in Week 1 — it silently shapes every week after this one.

Pick ONE:
- **Option A — Inspection reports.** Upload a scanned inspection sheet (an image or scanned PDF) plus a few SOP/reference manuals, and ask something like *"What maintenance action does this report require, based on our SOPs?"*
  - Why pick this: it's the more impressive, "wow factor" demo, and it exercises every module in the PRD (OCR, RAG, tool use, report generation).
  - Trade-off: you *must* build the OCR pipeline (Week 2) and it needs believable sample data — scanned-looking inspection sheets. If you don't have real ones, you'll need to fake realistic ones (e.g., write a fake inspection report in Word, print it, and photograph/scan it so it looks like a real scan).
- **Option B — HR/policy Q&A.** Upload an employee handbook or policy document, and ask questions like *"How many sick days am I entitled to?"*
  - Why pick this: it's simpler and lower-risk — you skip OCR entirely and go straight from typed PDF/DOCX text to chunking. Good choice if you're short on time or solo.
  - Trade-off: less visually dramatic in a demo, since there's no "look, it read a scanned photo!" moment.

**How to actually decide:** if you already have (or can easily fake) a handful of realistic scanned documents, go with Option A — it matches the PRD's "recommended" primary use case and gives a stronger story. If sourcing realistic scan samples feels like a time sink, default to Option B and note OCR as a "roadmap item," which the PRD explicitly allows as a fallback.

Whichever you pick, write it down in your own project notes now — you'll reference it constantly in Weeks 2, 4, and 8's demo script.

### Step 1.4 — Build a bare-bones backend
The backend is the "glue" between your webpage and the AI model. Right now you're not building any real features yet — just proving the wiring works, end to end, before adding complexity.

1. **Install Python 3.11.** Check your version with `python3 --version`. If you have an older version, install 3.11 specifically (via pyenv, or your OS package manager) — some libraries you'll use later expect this version.

2. **Create a clean project folder and a virtual environment**, so this project's Python packages don't clash with anything else on your machine:
   ```
   mkdir workbench-backend && cd workbench-backend
   python3.11 -m venv venv
   source venv/bin/activate      # on Windows: venv\Scripts\activate
   ```

3. **Install the two core libraries:**
   ```
   pip install fastapi uvicorn
   ```
   - **FastAPI** is the framework that defines your web routes (e.g., "when someone visits `/health`, do this").
   - **Uvicorn** is the actual server program that runs your FastAPI app and listens for requests.

4. **Write a minimal app.** Create a file called `main.py`:
   ```python
   from fastapi import FastAPI

   app = FastAPI()

   @app.get("/health")
   def health_check():
       return {"status": "ok"}
   ```

5. **Run it:**
   ```
   uvicorn main:app --reload
   ```
   The `--reload` flag automatically restarts the server whenever you save code changes — useful during development.

6. **Test it in your browser or terminal:** visit `http://localhost:8000/health` — you should see `{"status": "ok"}`. FastAPI also gives you free interactive API docs at `http://localhost:8000/docs`, which is worth bookmarking now since you'll use it constantly to test new routes as you add them.

7. **Prove the backend can talk to Ollama** — this is the real milestone for Week 1, since it connects the two things you've already installed. Add a second test route:
   ```python
   import requests

   @app.get("/test-ollama")
   def test_ollama():
       response = requests.post(
           "http://localhost:11434/api/generate",
           json={"model": "qwen2.5:7b-instruct-q4_K_M", "prompt": "Say hello in one sentence.", "stream": False}
       )
       return response.json()
   ```
   (Install `requests` first: `pip install requests`.) Visit `http://localhost:8000/test-ollama` — if you get back a real sentence from the model, your backend and your local AI engine are officially wired together.

**End of Week 1 checkpoint:** Docker and Ollama confirmed working (already done), demo scenario chosen and written down, FastAPI skeleton running, and a working test route proving your backend can successfully call your local Ollama model.

---

## Week 2 — Teach the System to Read Your Documents

**In simple terms:** Right now the AI can't see your files. This week you build the "upload and read" pipeline.

### Step 2.1 — Build a file upload endpoint
- Add a `/upload` route in FastAPI that accepts PDF, DOCX, and image files (`.pdf`, `.docx`, `.png`, `.jpg`).
- Use Python's `python-multipart` library to handle file uploads:
  ```
  pip install python-multipart
  ```

### Step 2.2 — Extract text from normal (typed) documents
- For PDFs: use `pdfplumber` or `PyPDF2` to pull out text.
- For Word docs: use `python-docx` to pull out paragraphs.
  ```
  pip install pdfplumber python-docx
  ```

### Step 2.3 — Extract text from scanned images (OCR)
OCR = "Optical Character Recognition" — it reads text out of a picture, like a scanned page.
- Install **Tesseract OCR** (a free, open-source OCR engine) on your system, plus the Python wrapper:
  ```
  pip install pytesseract pillow
  ```
- Write a function: if a file is an image (or a PDF made of scanned pages, no selectable text), run it through Tesseract to pull out the text.

### Step 2.4 — Break the text into small searchable pieces ("chunking")
AI models can't search a huge document all at once — you break it into small overlapping pieces (e.g., 500 words each) so it can find the relevant part later.
- Write a simple Python function using basic string-splitting, or use LangChain's built-in `RecursiveCharacterTextSplitter` if you want a ready-made tool:
  ```
  pip install langchain
  ```

### Step 2.5 — Test with real sample files
- Gather 5-10 sample documents matching your chosen demo scenario (SOPs + a scanned inspection sheet, OR an employee handbook).
- Run them through your pipeline and manually check: did it extract readable text? Did OCR work on the scanned page?

**End of Week 2 checkpoint:** You can upload a document (typed or scanned) and get back clean, chunked text.

---

## Week 3 — Make the AI Search Your Documents (RAG)

**In simple terms:** RAG stands for "Retrieval-Augmented Generation" — instead of the AI guessing answers from memory, it first *looks up* relevant text from your documents, then answers using that real text. This is what makes answers trustworthy instead of made-up.

### Step 3.1 — Turn text chunks into searchable numbers (embeddings)
An "embedding" is a way of converting a sentence into a list of numbers that captures its *meaning*, so a computer can compare how similar two pieces of text are.
- Pull an embedding model through Ollama:
  ```
  ollama pull nomic-embed-text
  ```
- Write a function that sends each text chunk to this model and gets back its embedding (a list of numbers).

### Step 3.2 — Store embeddings in a vector database
A vector database stores these number-lists and lets you quickly ask "which stored chunks are most similar to this new question?"
- Install **ChromaDB** (a free, local vector database):
  ```
  pip install chromadb
  ```
- Store each chunk's text + embedding + source filename + page number.

### Step 3.3 — Build the retrieval function
- Given a user's question, generate its embedding the same way, then ask ChromaDB for the "top 3-5 most similar" stored chunks.
- Return the chunk text AND its source (filename + page) — this source info becomes your citation later.

### Step 3.4 — Test retrieval quality
- Ask 10 sample questions you already know the answer to (from your test documents).
- Check: did it retrieve the *correct* chunk at least 8 out of 10 times? (This matches the PRD's "≥80% correctly sourced" target.)

**End of Week 3 checkpoint:** Asking a question returns the right supporting document chunks, with citations, at least 80% of the time.

---

## Week 4 — Build the "Agent" (the Decision-Maker)

**In simple terms:** So far you have a search engine, not an agent. An agent doesn't just search — it *decides* what to do: search documents? run a calculation? write a report? Then it double-checks its own answer before showing it to you.

### Step 4.1 — Set up the orchestration framework
- Install **LangGraph** (a framework for building step-by-step AI decision flows):
  ```
  pip install langgraph
  ```
- (Alternative if you want fewer dependencies: write a simple Python `if/else` state machine by hand — same idea, just manual.)

### Step 4.2 — Build the agent's steps as a flow
1. **Classify the question** — is this a document question, a calculation, or both?
2. **Retrieve context** — call your Week 3 retrieval function.
3. **Decide if a tool is needed** — e.g., does the question involve a number/calculation?
4. **Draft an answer** — send the question + retrieved chunks to your Ollama model, ask it to answer using ONLY that context.
5. **Validate the answer** — check that the AI's claims can be traced back to a retrieved chunk. If not, the agent should say "not found in provided documents" instead of guessing.

### Step 4.3 — Add tools (giving the agent "hands")
Pick 2-3 tools:
- **Calculator tool:** use Python's `numexpr` (safe math evaluation) or `pandas` for data calculations.
  ```
  pip install numexpr pandas
  ```
- **Document search tool:** just wraps your Week 3 retrieval function so the agent can call it as an action.
- **Report writer tool:** a function that formats the final answer into a structured report (built fully in Week 6).

### Step 4.4 — Test the full agent flow
- Ask a question that needs BOTH document lookup AND a calculation (e.g., "Based on the SOP's wear tolerance limit, does this measurement of 4.2mm pass or fail?").
- Confirm the agent uses both tools correctly without you manually telling it to.

**End of Week 4 checkpoint:** One working end-to-end agent flow using at least 2 tools automatically.

---

## Week 5 — Build the Website (Frontend)

**In simple terms:** Everything so far only works through code/terminal. Now you build the actual webpage people click around in.

### Step 5.1 — Set up the frontend project
- Install **Node.js**, then create a React project:
  ```
  npx create-next-app@latest workbench-frontend
  ```
  (Or use **Vite** instead of Next.js if you want something lighter: `npm create vite@latest`.)

### Step 5.2 — Build the login page
- A simple form: username + password fields, a "Login" button.
- On submit, send credentials to your backend's login endpoint (built in Week 1's security add-on, see Week 6).

### Step 5.3 — Build the upload page
- A drag-and-drop or "choose file" button that sends the file to your `/upload` backend endpoint from Week 2.
- Show a simple success message once the file is processed.

### Step 5.4 — Build the chat interface
- A text box where the user types a question, a "Send" button, and a scrolling area showing the conversation.
- Each AI answer should visibly show its citations (e.g., "Source: SOP-Manual.pdf, page 4").

### Step 5.5 — Build the audit log viewer page
- A simple table showing past requests: time, question asked, sources used, tools called. (The actual logging happens in Week 6 — this page just displays it.)

**End of Week 5 checkpoint:** A working website where you can log in, upload a file, ask a question, and see a formatted answer with citations.

---

## Week 6 — Add Security, Logging, and Report Generation

**In simple terms:** This week adds the "trust" features — proving who did what, and turning answers into a shareable document.

### Step 6.1 — Add login security
- Install password-hashing and token libraries:
  ```
  pip install passlib[bcrypt] python-jose
  ```
- Store one admin username + a bcrypt-hashed password (never store plain-text passwords).
- On successful login, issue a **JWT token** (a signed digital "pass") that the frontend includes in future requests to prove the user is logged in.

### Step 6.2 — Build the audit log database
- Use **SQLite** (simplest — just a single file, no extra setup) or PostgreSQL if you want something closer to a "real" production database.
  ```
  pip install sqlalchemy
  ```
- Create one table with columns: `timestamp`, `user`, `question`, `sources_used`, `tools_called`, `final_answer`.
- Every time the agent finishes answering, write one row into this table.

### Step 6.3 — Lock the system to local-only network access
- In your FastAPI/Uvicorn startup config, bind only to `127.0.0.1` or your local network IP — never `0.0.0.0` with a public-facing setup.
- This ensures nothing is reachable from the internet, only from your own machine/network.

### Step 6.4 — Build the report generator
- Install:
  ```
  pip install python-docx reportlab
  ```
- Write a function that takes the agent's final answer + citations and fills them into a template:
  - **python-docx** → generates a Word (.docx) report.
  - **reportlab** → generates a PDF report.
- Include a "Sources" section listing every document/page cited.

**End of Week 6 checkpoint:** Every question is logged with full traceability, and answers can be exported as a real Word/PDF report.

---

## Week 7 — Package Everything and Prove It's Offline

**In simple terms:** Now you make the whole system start with one command, and prove — with evidence — that no data leaves your computer.

### Step 7.1 — Write your Docker Compose file
- Create a `docker-compose.yml` that starts: the backend, the frontend, Ollama, and the database — all together.
- Test it on a clean machine (or after deleting all containers) with:
  ```
  docker compose up --build
  ```
- Confirm the whole app comes up and works from this single command.

### Step 7.2 — Prove zero internet usage
- Install and open **Wireshark** (a free network traffic monitor) or simply run **netstat** in a terminal while using the app.
- Run through a full demo question (upload → ask → get report) while watching the monitor — confirm no outbound connections to the internet appear.
- For the strongest proof: physically unplug your Ethernet cable / turn off Wi-Fi, then run the same demo. If it still works, that's undeniable proof of "sovereignty."

### Step 7.3 — Full integration testing
- Run through your entire demo scenario at least 5-10 times end to end.
- Fix any crashes, slow points, or wrong citations you find.
- Time each query — the target is under 30 seconds per response on your hardware.

**End of Week 7 checkpoint:** One-command startup works, and you have proof (screenshots/video) of zero network activity during a full demo run.

---

## Week 8 — Rehearse and Polish for the Demo

**In simple terms:** This week isn't about new features — it's about making sure the demo goes smoothly in front of your mentor.

### Step 8.1 — Pre-test your exact demo questions
- Decide the 3-5 exact questions you'll ask live.
- Run them ahead of time and note how long each takes and what the answer looks like — no surprises during the live demo.

### Step 8.2 — Write your demo script
Follow this flow (from the PRD):
1. Upload the scanned inspection report/handbook + reference documents (live, in front of the mentor).
2. Ask your prepared question out loud.
3. Show the agent's answer with visible citations.
4. Show the generated Word/PDF report.
5. Show the audit log entry for that exact request.
6. Show the network monitor (or the unplugged cable) proving zero internet use.

### Step 8.3 — Prepare for questions
- Be ready to explain: why local AI (data privacy), what "agentic" means here (tool use + self-checking), and what's out of scope for this version (multi-user accounts, enterprise login, fine-tuning, etc.) so it's clear what's MVP vs. future work.

### Step 8.4 — Final polish
- Clean up any obvious UI rough edges.
- Make sure error cases (e.g., no matching document found) show a graceful message, not a crash.

**End of Week 8 checkpoint:** A rehearsed, reliable demo ready to present.

---

## Quick Reference — All Tools Used, By Week

| Week | Main Tools/Libraries |
|---|---|
| 1 | Docker, Ollama, Qwen2.5-7B, Llama-3.2-3B, Python 3.11, FastAPI, Uvicorn |
| 2 | python-multipart, pdfplumber, python-docx, Tesseract OCR, pytesseract, LangChain (optional) |
| 3 | nomic-embed-text (via Ollama), ChromaDB |
| 4 | LangGraph, numexpr, pandas |
| 5 | Node.js, React, Next.js (or Vite) |
| 6 | passlib (bcrypt), python-jose (JWT), SQLite/PostgreSQL, SQLAlchemy, python-docx, reportlab |
| 7 | Docker Compose, Wireshark or netstat |
| 8 | (No new tools — testing and rehearsal only) |

**Total cost if you already own a decent laptop/PC: $0.**
