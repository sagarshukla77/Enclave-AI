from fastapi import FastAPI
from pydantic import BaseModel
from app.agent_interface import run_agent
 
app = FastAPI(title="ENCLAVE AI")
 
class ChatRequest(BaseModel):
    question: str
    model: str = "qwen2.5"
 
@app.get("/health")
def health():
    return {"status": "ok"}
 
@app.post("/chat")
def chat(req: ChatRequest):
    return run_agent(req.question, "admin", req.model)


from app.database import init_db
 
@app.on_event("startup")
def startup():
    init_db()
