"""Calculator tool — safe mathematical expression evaluator."""

import ast
import math
import operator
from typing import Annotated

from langchain_core.tools import tool
from pydantic import BaseModel, Field


# Allowed operators for safe evaluation
_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Allowed math functions
_SAFE_FUNCS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval(node: ast.AST) -> float:
    """Recursively evaluate an AST node using only safe operations."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name) and node.id in _SAFE_FUNCS:
        val = _SAFE_FUNCS[node.id]
        if isinstance(val, (int, float)):
            return float(val)
        raise ValueError(f"'{node.id}' is a function, not a constant")
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _SAFE_OPS[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        operand = _safe_eval(node.operand)
        return _SAFE_OPS[op_type](operand)
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls are allowed")
        func_name = node.func.id
        if func_name not in _SAFE_FUNCS:
            raise ValueError(f"Unknown function: {func_name}")
        func = _SAFE_FUNCS[func_name]
        if not callable(func):
            raise ValueError(f"'{func_name}' is not callable")
        args = [_safe_eval(a) for a in node.args]
        return float(func(*args))
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


@tool
def calculator(
    expression: Annotated[str, "A mathematical expression to evaluate, e.g. '(2+3)*4' or 'sqrt(144)'"],
) -> str:
    """Evaluate a mathematical expression safely.

    Supports: +, -, *, /, //, %, ** and functions like sqrt, log, sin, cos, tan, abs, round, min, max.
    Constants: pi, e.

    Examples:
      - "2 + 3 * 4" → "14.0"
      - "sqrt(144)" → "12.0"
      - "log(100, 10)" → "2.0"
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _safe_eval(tree)
        # Format cleanly: drop .0 for integers
        if result == int(result):
            return str(int(result))
        return f"{result:.10g}"
    except (ValueError, TypeError, ZeroDivisionError, SyntaxError) as exc:
        return f"Error: {exc}"
