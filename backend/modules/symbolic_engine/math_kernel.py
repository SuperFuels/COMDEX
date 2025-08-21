import math
from typing import Union, Dict, Any, List, Tuple, Optional

from sympy import (
    sympify, simplify, solve, Symbol, Eq, symbols, diff, integrate,
    Matrix, latex, pretty, limit, nsimplify, Derivative, Integral,
    series, solveset, S, And, Or
)
from sympy.core.sympify import SympifyError
from sympy.parsing.sympy_parser import parse_expr


class MathKernel:
    def __init__(self):
        self.env: Dict[str, Union[float, str]] = {}

    # --- Basic Numeric Evaluation ---
    def evaluate(self, expr: str) -> Union[float, str]:
        try:
            result = sympify(expr, evaluate=True).evalf()
            return float(result)
        except Exception:
            return "❌ Invalid expression"

    def simplify_expr(self, expr: str) -> str:
        try:
            simplified = simplify(sympify(expr))
            return str(simplified)
        except Exception:
            return "❌ Cannot simplify"

    def symbolic_substitute(self, expr: str, substitutions: Dict[str, Union[float, str]]) -> str:
        try:
            parsed = sympify(expr)
            subs = {Symbol(k): sympify(v) for k, v in substitutions.items()}
            result = parsed.subs(subs)
            return str(result)
        except Exception:
            return "❌ Failed to substitute"

    # --- Algebraic Solving ---
    def solve_equation(self, lhs: str, rhs: str = "0") -> List[str]:
        try:
            symbols_in_expr = sympify(lhs + "+" + rhs).free_symbols
            eq = Eq(sympify(lhs), sympify(rhs))
            sol = solve(eq, list(symbols_in_expr) or Symbol("x"))
            return [str(s) for s in sol]
        except Exception:
            return ["❌ Unable to solve"]

    def solve_system(self, equations: List[Tuple[str, str]]) -> Dict[str, str]:
        try:
            syms = set()
            eqs = []
            for lhs, rhs in equations:
                eq = Eq(sympify(lhs), sympify(rhs))
                eqs.append(eq)
                syms.update(eq.free_symbols)
            sol = solve(eqs, list(syms))
            return {str(k): str(v) for k, v in sol.items()}
        except Exception:
            return {"error": "❌ Failed to solve system"}

    def boolean_solve(self, expr: str, var: str = "x") -> str:
        try:
            x = Symbol(var)
            result = solveset(sympify(expr), x, domain=S.Reals)
            return str(result)
        except Exception:
            return "❌ Failed to solve boolean condition"

    # --- Calculus ---
    def derivative(self, expr: str, var: str = "x", order: int = 1) -> str:
        try:
            x = Symbol(var)
            result = sympify(expr)
            for _ in range(order):
                result = diff(result, x)
            return str(result)
        except Exception:
            return "❌ Failed to compute derivative"

    def integral(self, expr: str, var: str = "x", definite: Optional[Tuple[str, str]] = None) -> str:
        try:
            x = Symbol(var)
            parsed = sympify(expr)
            if definite:
                a = sympify(definite[0])
                b = sympify(definite[1])
                result = integrate(parsed, (x, a, b))
            else:
                result = integrate(parsed, x)
            return str(result)
        except Exception:
            return "❌ Failed to compute integral"

    def compute_limit(self, expr: str, var: str = "x", point: Union[str, float] = "0") -> str:
        try:
            x = Symbol(var)
            p = sympify(point)
            return str(limit(sympify(expr), x, p))
        except Exception:
            return "❌ Failed to compute limit"

    def taylor_series(self, expr: str, var: str = "x", point: Union[str, float] = "0", order: int = 5) -> str:
        try:
            x = Symbol(var)
            p = sympify(point)
            result = series(sympify(expr), x, p, order)
            return str(result.removeO())
        except Exception:
            return "❌ Failed to compute series"

    # --- Matrix Operations ---
    def matrix_ops(self, matrix_list: List[List[Union[int, float]]], operation: str) -> Union[str, List[List[float]]]:
        try:
            m = Matrix(matrix_list)
            if operation == "det":
                return str(m.det())
            elif operation == "inv":
                return m.inv().tolist()
            elif operation == "transpose":
                return m.transpose().tolist()
            else:
                return "❌ Unknown operation"
        except Exception:
            return "❌ Matrix error"

    # --- Numeric Approximation ---
    def approximate_numeric_system(self, equations: List[Tuple[str, str]], guess: Dict[str, float]) -> Dict[str, str]:
        try:
            from sympy import nsolve
            vars = list({Symbol(k) for k in guess})
            funcs = [Eq(sympify(lhs), sympify(rhs)) for lhs, rhs in equations]
            guess_vector = [guess[str(v)] for v in vars]
            sol = nsolve(funcs, vars, guess_vector)
            return {str(vars[i]): str(sol[i]) for i in range(len(vars))}
        except Exception:
            return {"error": "❌ Approximation failed"}

    # --- Definitions ---
    def define(self, symbol: str, value: Union[float, str]):
        try:
            self.env[symbol] = value
        except Exception:
            pass

    def get_env(self) -> Dict[str, Union[float, str]]:
        return self.env

    # --- Output Formatting ---
    def format_latex(self, expr: str) -> str:
        try:
            return latex(sympify(expr))
        except Exception:
            return "❌ Invalid expression"

    def format_pretty(self, expr: str) -> str:
        try:
            return pretty(sympify(expr))
        except Exception:
            return "❌ Invalid expression"

    # --- Trace + Debug ---
    def trace_steps(self, expr: str) -> List[str]:
        steps = []
        try:
            parsed = sympify(expr)
            steps.append(f"Start: {parsed}")
            simplified = simplify(parsed)
            if simplified != parsed:
                steps.append(f"Simplified: {simplified}")
            result = simplified.evalf()
            steps.append(f"Evaluated: {result}")
        except Exception:
            steps.append("❌ Failed to trace steps")
        return steps

    def trace_with_metadata(self, expr: str) -> Dict[str, Any]:
        try:
            parsed = sympify(expr)
            simplified = simplify(parsed)
            evaluated = simplified.evalf()
            return {
                "input": expr,
                "parsed": str(parsed),
                "simplified": str(simplified),
                "evaluated": float(evaluated),
                "latex": self.format_latex(str(simplified)),
                "trace": self.trace_steps(expr),
                "metadata": {
                    "vars": list(map(str, parsed.free_symbols)),
                    "type": str(type(parsed)),
                    "depth": len(str(parsed))
                }
            }
        except Exception:
            return {
                "error": "❌ Failed to trace with metadata",
                "input": expr
            }