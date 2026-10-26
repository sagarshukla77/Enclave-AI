"""Start the backend, bound to this machine only."""
from pathlib import Path

import uvicorn

HERE = Path(__file__).resolve().parent

if __name__ == "__main__":
    # 127.0.0.1 = reachable only from this computer. Never use 0.0.0.0 on a public network.
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True,
                reload_dirs=[str(HERE), str(HERE.parent / "ai-core")])
