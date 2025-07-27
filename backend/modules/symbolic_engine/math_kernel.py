# 📁 backend/modules/symbolic_engine/math_kernel.py

import math
import operator
from typing import Union, Dict, Any, List, Tuple, Optional

from sympy import (
    sympify, simplify, solve, Symbol, Eq, symbols, diff, integrate,
    Matrix, latex, pretty, S, Derivative, Integral, limit, nsimplify
)
from sympy.parsing.sympy_parser import parse_expr
from sympy.core.sympify import SympifyError


class MathKernel:
    def __init__(self):
        self.env: Dict[str, Union[float, str]] = {}

    def evaluate(self, expr: str) -> Union[float, str]:
        """
        Numerically evaluates a math expression.
        """
        try:
            result = sympify(expr, evaluate=True).evalf()
            return float(result)
        except Exception:
            return "❌ Invalid expression"

    def simplify_expr(self, expr: str) -> str:
        """
        Returns simplified symbolic expression.
        """
        try:
            simplified = simplify(sympify(expr))
            return str(simplified)
        except Exception:
            return "❌ Cannot simplify"

    def solve_equation(self, lhs: str, rhs: str = "0") -> List[str]:
        """
        Solves lhs = rhs and returns solutions as strings.
        """
        try:
            symbols_in_expr = sympify(lhs + "+" + rhs).free_symbols
            eq = Eq(sympify(lhs), sympify(rhs))
            sol = solve(eq, list(symbols_in_expr) or Symbol("x"))
            return [str(s) for s in sol]
        except Exception:
            return ["❌ Unable to solve"]

    def solve_system(self, equations: List[Tuple[str, str]]) -> Dict[str, str]:
        """
        Solves a system of equations like:
        [("x + y", "3"), ("x - y", "1")]
        """
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

    def derivative(self, expr: str, var: str = "x") -> str:
        try:
            x = Symbol(var)
            return str(diff(sympify(expr), x))
        except Exception:
            return "❌ Failed to compute derivative"

    def integral(self, expr: str, var: str = "x") -> str:
        try:
            x = Symbol(var)
            return str(integrate(sympify(expr), x))
        except Exception:
            return "❌ Failed to compute integral"

    def compute_limit(self, expr: str, var: str = "x", point: Union[str, float] = "0") -> str:
        try:
            x = Symbol(var)
            p = sympify(point)
            return str(limit(sympify(expr), x, p))
        except Exception:
            return "❌ Failed to compute limit"

    def matrix_ops(self, matrix_list: List[List[Union[int, float]]], operation: str) -> Union[str, List[List[float]]]:
        """
        Basic matrix operations: 'det', 'inv', 'transpose'
        """
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

    def define(self, symbol: str, value: Union[float, str]):
        """
        Define or update a variable.
        """
        try:
            self.env[symbol] = value
        except Exception:
            pass

    def get_env(self) -> Dict[str, Union[float, str]]:
        return self.env

    def format_latex(self, expr: str) -> str:
        """
        Returns the LaTeX string for the expression (for UI rendering).
        """
        try:
            return latex(sympify(expr))
        except Exception:
            return "❌ Invalid expression"

    def format_pretty(self, expr: str) -> str:
        """
        Pretty ASCII formatting for CLI / log output.
        """
        try:
            return pretty(sympify(expr))
        except Exception:
            return "❌ Invalid expression"

    def trace_steps(self, expr: str) -> List[str]:
        """
        Returns a symbolic simplification trace.
        This is a linear reduction; full step logic requires an external trace engine.
        """
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