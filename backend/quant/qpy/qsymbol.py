# ================================================================
# 🌊 QSymbol - Symbolic primitive wrapper
# ================================================================
from sympy import Symbol

class QSymbol:
    """Resonance-safe symbolic variable."""
    def __init__(self, name: str):
        self.sym = Symbol(name)

    def __repr__(self):
        return f"QSymbol({self.sym})"

    def to_sympy(self):
        return self.sym