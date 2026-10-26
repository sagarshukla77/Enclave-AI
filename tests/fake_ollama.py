"""A tiny stand-in for Ollama so the backend can be tested without a GPU/model.

Run:  python tests/fake_ollama.py   (listens on 127.0.0.1:11434 - stop the real Ollama first)
Embeddings are a hashed bag-of-words, so retrieval genuinely works; the "LLM" answers
by quoting the top source. Only for testing - real answers come from the real model.
"""
import hashlib
import json
import math
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

DIM = 256


def embed(text: str) -> list[float]:
    v = [0.0] * DIM
    for w in re.findall(r"[a-z0-9\.]+", text.lower()):
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % DIM] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def fake_generate(prompt: str, fmt: str | None) -> str:
    if fmt == "json" and "Classify the user's question" in prompt:
        q = prompt.split("Question:")[-1]
        return json.dumps({"task": "both" if re.search(r"\d", q) and re.search(r"pass|fail|exceed", q, re.I) else "document"})
    if fmt == "json":                                   # calculator expression request
        q = prompt.split("Question:")[-1]
        nums = re.findall(r"\d+\.\d+|\d+", q)
        return json.dumps({"expression": f"{nums[0]} > 3.5" if nums else "", "meaning": "measurement exceeds limit"})
    if "[S1]" in prompt and "NOT_FOUND" in prompt:
        m = re.search(r"\[S1\][^\n]*\n(.+?)(?:\n\n|\Z)", prompt, re.S)
        calc = re.search(r"Calculator result \(trusted\): (.+?) =", prompt)
        extra = " The calculator check returned True, so it FAILS the limit." if calc else ""
        return f"Based on the SOP: {m.group(1).strip()[:160]} [S1].{extra}" if m else "NOT_FOUND"
    return "Hello!"


class H(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        self._send({"models": [{"name": "qwen2.5:7b-instruct-q4_K_M"}, {"name": "nomic-embed-text:latest"}]})

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/embed":
            self._send({"embeddings": [embed(t) for t in data["input"]]})
        elif self.path == "/api/generate" and data.get("images"):
            self._send({"response": "VISION READ: Measured impeller wear 4.2 mm (handwritten note)"})
        elif self.path == "/api/generate":
            self._send({"response": fake_generate(data["prompt"], data.get("format"))})
        else:
            self._send({"error": "unknown"}, 404)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("Fake Ollama on http://127.0.0.1:11434")
    HTTPServer(("127.0.0.1", 11434), H).serve_forever()
