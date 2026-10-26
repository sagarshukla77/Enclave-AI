"""Tool execution layer (Week 4, step 4.3): calculator + document search."""
import re

import numexpr

from . import rag

# Only digits, dots, spaces, arithmetic/comparison operators and parentheses are allowed.
# Letters are rejected outright, so numexpr can never be asked to touch names or functions.
_SAFE_EXPR = re.compile(r"^[0-9\.\s\+\-\*/\(\)%<>=!&|]+$")


class ToolError(ValueError):
    pass


def calculator(expression: str) -> dict:
    """Safely evaluate a math/comparison expression, e.g. '4.2 > 3.5' or '(12.5-9)/12.5*100'."""
    expr = (expression or "").strip().replace("^", "**").replace("×", "*").replace("÷", "/")
    if not expr:
        raise ToolError("Empty expression.")
    if len(expr) > 200 or not _SAFE_EXPR.match(expr):
        raise ToolError(f"Expression contains unsupported characters: {expression!r}")
    try:
        value = numexpr.evaluate(expr, local_dict={}, global_dict={}).item()
    except Exception as e:  # bad syntax, division problems, etc.
        raise ToolError(f"Could not evaluate {expression!r}: {e}")
    if isinstance(value, float):
        value = round(value, 6)
    return {"expression": expr, "result": value}


def document_search(query: str, k: int | None = None) -> list[dict]:
    """Search the knowledge base (thin wrapper so the agent can call it as a tool)."""
    return rag.retrieve(query, k=k)
