from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.agent_interface import run_agent
from app.database import init_db
from app import auth
from app import audit


app = FastAPI(title="ENCLAVE AI")


class ChatRequest(BaseModel):
    question: str
    model: str = "qwen2.5"


@app.on_event("startup")
def startup():
    init_db()
    auth.create_admin_if_missing()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = auth.authenticate(form.username, form.password)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Wrong username or password"
        )

    return {
        "access_token": auth.create_token(user),
        "token_type": "bearer"
    }


@app.post("/chat")
def chat(
    req: ChatRequest,
    user: str = Depends(auth.get_current_user)
):
    try:
        result = run_agent(req.question, user, req.model)

        audit.log_request(
            user,
            req.question,
            result.get("sources", []),
            result.get("tools_used", []),
            result.get("answer", "")
        )

        return result

    except Exception as e:

        # Log failed requests as well
        audit.log_request(
            user,
            req.question,
            [],
            [],
            f"ERROR: {str(e)}"
        )

        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request."
        )


@app.get("/audit")
def get_audit(
    limit: int = 100,
    user: str = Depends(auth.get_current_user)
):
    return audit.get_recent(limit)