"""Agent orchestrator (Week 4): classify -> retrieve -> [calculate] -> draft -> validate.

Built as a LangGraph state graph. If LangGraph is not installed the same nodes run
in a plain Python sequence, so behaviour is identical either way.
"""
import json
import re
import time
from typing import TypedDict

from . import config, llm, tools

try:
    from langgraph.graph import END, StateGraph
    HAVE_LANGGRAPH = True
except Exception:  # pragma: no cover
    HAVE_LANGGRAPH = False

NOT_FOUND = "Not found in provided documents."
MIN_SCORE = 0.20            # ignore retrieved chunks less similar than this
CALC_HINTS = re.compile(
    r"\b(calculate|compute|sum|total|average|percent|percentage|difference|ratio|pass|fail|"
    r"exceed\w*|within|tolerance|limit|threshold|less than|greater than|above|below|remaining)\b", re.I)


class AgentState(TypedDict, total=False):
    question: str
    model: str
    task_type: str            # document | calculation | both
    chunks: list
    calc: dict | None
    tools_called: list
    draft: str
    answer: str
    citations: list
    validation: dict
    trace: list


# ---------------------------------------------------------------- helpers
def _log(state: AgentState, step: str, detail: str) -> None:
    state.setdefault("trace", []).append({"step": step, "detail": detail, "t": round(time.time(), 2)})


def _json_from(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {}


def _context_block(chunks: list) -> str:
    return "\n\n".join(f"[S{i}] (file: {c['source']}, page {c['page']})\n{c['text']}"
                       for i, c in enumerate(chunks, start=1))


# ---------------------------------------------------------------- nodes
def classify(state: AgentState) -> AgentState:
    q = state["question"]
    task = None
    try:
        raw = llm.generate(
            "Classify the user's question. Reply with JSON only: "
            '{"task": "document" | "calculation" | "both"}.\n'
            '"document" = answer is found by reading documents; '
            '"calculation" = needs only arithmetic; '
            '"both" = needs document facts AND a numeric calculation/comparison '
            "(e.g. does a measurement pass a limit).\n"
            f"Question: {q}", model=state["model"], json_mode=True)
        task = _json_from(raw).get("task")
    except llm.OllamaError:
        raise
    except Exception:
        task = None
    if task not in {"document", "calculation", "both"}:      # fallback heuristic
        has_number = bool(re.search(r"\d", q))
        task = "both" if (has_number and CALC_HINTS.search(q)) else "document"
    state["task_type"] = task
    _log(state, "classify", f"task type = {task}")
    return state


def retrieve(state: AgentState) -> AgentState:
    results = tools.document_search(state["question"])
    kept = [c for c in results if c["score"] >= MIN_SCORE]
    state["chunks"] = kept
    state.setdefault("tools_called", []).append({
        "tool": "document_search", "input": state["question"],
        "output": f"{len(kept)} chunk(s): " + ", ".join(f"{c['source']} p{c['page']}" for c in kept),
    })
    _log(state, "retrieve", f"{len(kept)} relevant chunk(s) of {len(results)} retrieved")
    return state


def route_after_retrieve(state: AgentState) -> str:
    if not state.get("chunks") and state["task_type"] == "document":
        return "draft"                      # nothing found -> draft/validate will say "not found"
    return "calculate" if state["task_type"] in {"calculation", "both"} else "draft"


def calculate(state: AgentState) -> AgentState:
    ctx = _context_block(state.get("chunks", [])) or "(no documents retrieved)"
    raw = llm.generate(
        "You convert a question into ONE arithmetic or comparison expression for a calculator.\n"
        "Use only numbers that appear in the question or the sources. Use only digits, + - * / "
        "( ) and comparison operators (< <= > >= ==). No units, no words.\n"
        'Reply JSON only: {"expression": "...", "meaning": "what the expression checks"}. '
        'If no calculation is possible reply {"expression": "", "meaning": ""}.\n\n'
        f"Sources:\n{ctx}\n\nQuestion: {state['question']}",
        model=state["model"], json_mode=True)
    spec = _json_from(raw)
    expr = str(spec.get("expression", "")).strip()
    if not expr:
        _log(state, "calculate", "no calculation needed/possible")
        return state
    try:
        result = tools.calculator(expr)
        result["meaning"] = spec.get("meaning", "")
        state["calc"] = result
        summary = f"{result['expression']} = {result['result']}"
    except tools.ToolError as e:
        state["calc"] = {"expression": expr, "error": str(e)}
        summary = f"failed: {e}"
    state.setdefault("tools_called", []).append({"tool": "calculator", "input": expr, "output": summary})
    _log(state, "calculate", summary)
    return state


def draft(state: AgentState) -> AgentState:
    chunks = state.get("chunks", [])
    if not chunks:
        state["draft"] = "NOT_FOUND"
        _log(state, "draft", "no evidence retrieved")
        return state
    calc_txt = ""
    calc = state.get("calc")
    if calc and "result" in calc:
        calc_txt = (f"\nCalculator result (trusted): {calc['expression']} = {calc['result']}"
                    f" ({calc.get('meaning', '')}). True means the condition holds.\n")
    prompt = (
        "You are a careful assistant for an engineering/operations team.\n"
        "Answer the question using ONLY the numbered sources below.\n"
        "Rules: cite every claim with its source tag like [S1] or [S2]; do not invent facts or "
        "numbers; if the sources do not contain the answer, reply exactly: NOT_FOUND\n"
        f"\nSources:\n{_context_block(chunks)}\n{calc_txt}\nQuestion: {state['question']}\n\nAnswer:"
    )
    state["draft"] = llm.generate(prompt, model=state["model"], temperature=0.1)
    _log(state, "draft", f"{len(state['draft'])} characters")
    return state


def validate(state: AgentState) -> AgentState:
    """Check the draft is traceable to retrieved evidence; otherwise refuse to guess."""
    text = state.get("draft", "").strip()
    chunks = state.get("chunks", [])
    issues: list[str] = []

    def fail(reason: str) -> AgentState:
        state["answer"], state["citations"] = NOT_FOUND, []
        state["validation"] = {"passed": False, "issues": [reason], "cited_sources": []}
        _log(state, "validate", f"rejected: {reason}")
        return state

    if not chunks:
        return fail("no relevant document chunks were retrieved")
    if not text or "NOT_FOUND" in text.upper().replace(" ", "_"):
        return fail("model reported the answer is not in the documents")

    cited = sorted({int(n) for n in re.findall(r"\[S(\d+)\]", text) if 1 <= int(n) <= len(chunks)})
    context = " ".join(c["text"] for c in chunks).lower()

    # lexical grounding: what share of the answer's content words appear in the evidence?
    words = [w for w in re.findall(r"[a-zA-Z]{4,}", re.sub(r"\[S\d+\]", "", text).lower())]
    overlap = (sum(w in context for w in words) / len(words)) if words else 0.0
    if not cited and overlap < 0.5:
        return fail(f"no valid citation and only {overlap:.0%} of the wording is supported by sources")
    if not cited:
        issues.append("answer had no explicit [S#] citation; matched to sources by wording")
        cited = list(range(1, len(chunks) + 1))

    # numbers in the answer should come from sources, the question, or the calculator
    allowed = context + " " + state["question"].lower() + " " + json.dumps(state.get("calc") or {})
    for num in set(re.findall(r"\d+(?:\.\d+)?", re.sub(r"\[S\d+\]", "", text))):
        if num not in allowed:
            issues.append(f"number {num} in the answer was not found in the sources")

    state["answer"] = text
    state["citations"] = [{
        "label": f"S{i}", "source": chunks[i - 1]["source"], "page": chunks[i - 1]["page"],
        "score": chunks[i - 1]["score"], "text": chunks[i - 1]["text"],
    } for i in cited]
    state["validation"] = {"passed": not issues, "issues": issues,
                           "cited_sources": [f"{chunks[i-1]['source']} (p{chunks[i-1]['page']})" for i in cited],
                           "grounding": round(overlap, 2)}
    _log(state, "validate", "passed" if not issues else "passed with warnings: " + "; ".join(issues))
    return state


# ---------------------------------------------------------------- graph
def _build_graph():
    g = StateGraph(AgentState)
    for name, fn in [("classify", classify), ("retrieve", retrieve), ("calculate", calculate),
                     ("draft", draft), ("validate", validate)]:
        g.add_node(name, fn)
    g.set_entry_point("classify")
    g.add_edge("classify", "retrieve")
    g.add_conditional_edges("retrieve", route_after_retrieve, {"calculate": "calculate", "draft": "draft"})
    g.add_edge("calculate", "draft")
    g.add_edge("draft", "validate")
    g.add_edge("validate", END)
    return g.compile()


_GRAPH = _build_graph() if HAVE_LANGGRAPH else None


def run_agent(question: str, model: str | None = None) -> dict:
    state: AgentState = {"question": question.strip(), "model": model or config.LLM_MODEL,
                         "tools_called": [], "trace": [], "calc": None}
    started = time.time()
    if _GRAPH is not None:
        state = _GRAPH.invoke(state)
    else:
        state = classify(state)
        state = retrieve(state)
        if route_after_retrieve(state) == "calculate":
            state = calculate(state)
        state = validate(draft(state))
    state["duration_seconds"] = round(time.time() - started, 1)
    return state
