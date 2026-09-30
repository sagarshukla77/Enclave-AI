import os
from datetime import datetime, timedelta, timezone
 
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
 
from app.database import get_connection
 
load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET", "dev-only-change-me")
ALGORITHM = "HS256"
EXPIRE_HOURS = 8
 
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
 
def hash_password(password: str) -> str:
    return pwd_context.hash(password)
 
def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)
 
def create_admin_if_missing():
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD")
    if not password:
        raise RuntimeError("Set ADMIN_PASSWORD in .env")
    conn = get_connection()
    row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if row is None:
        conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                     (username, hash_password(password)))
        conn.commit()
    conn.close()
 
def authenticate(username: str, password: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if row and verify_password(password, row["password_hash"]):
        return row["username"]
    return None
 
def create_token(username: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": expires}, SECRET_KEY, algorithm=ALGORITHM)
 
def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    return username
