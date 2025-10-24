# ================================================================
# 🔗 QPy SymPy Compatibility Layer
# ================================================================
from sympy import sin, cos, diff, simplify

def qsin(x): return sin(x)
def qcos(x): return cos(x)
def qdiff(expr, var): return diff(expr, var)
def qsimplify(expr): return simplify(expr)