# ================================================================
# 🧩 QPy Facade
# ================================================================
import logging
from sympy import simplify

logger = logging.getLogger(__name__)

class QPy:
    """Central dispatch layer for symbolic / numeric operations."""

    @staticmethod
    def eval(expr):
        logger.info("[QPy] Route op -> SymPy.simplify()")
        return simplify(expr)