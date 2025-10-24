# ================================================================
# 🧠 QuantPy Compatibility: Logic & Simplification Layer
# ================================================================
"""
Provides safe SymPy logic compatibility for QuantPy v0.5 transition.

This acts as a drop-in bridge so legacy code using sympy.boolalg
can transparently call QuantPy logic operators.

Exports:
    qand, qor, qnot, qimplies, qequiv
    qsimplify_logic, qto_cnf, qto_dnf
"""

import sympy as sp
from sympy.logic.boolalg import And, Or, Not, Implies, Equivalent, simplify_logic, to_cnf, to_dnf


# ----------------------------------------------------------------------
# Logic operator wrappers
# ----------------------------------------------------------------------
def qand(*args):
    """QuantPy boolean AND."""
    return And(*args)


def qor(*args):
    """QuantPy boolean OR."""
    return Or(*args)


def qnot(arg):
    """QuantPy boolean NOT."""
    return Not(arg)


def qimplies(a, b):
    """QuantPy boolean implication."""
    return Implies(a, b)


def qequiv(a, b):
    """QuantPy boolean equivalence."""
    return Equivalent(a, b)


# ----------------------------------------------------------------------
# Simplification / normalization
# ----------------------------------------------------------------------
def qsimplify_logic(expr, form="cnf"):
    """Simplify boolean expressions."""
    return simplify_logic(expr, form=form)


def qto_cnf(expr, simplify=True):
    """Convert to CNF form."""
    return to_cnf(expr, simplify=simplify)


def qto_dnf(expr, simplify=True):
    """Convert to DNF form."""
    return to_dnf(expr, simplify=simplify)


# ----------------------------------------------------------------------
# Compatibility info
# ----------------------------------------------------------------------
__all__ = [
    "qand",
    "qor",
    "qnot",
    "qimplies",
    "qequiv",
    "qsimplify_logic",
    "qto_cnf",
    "qto_dnf",
]