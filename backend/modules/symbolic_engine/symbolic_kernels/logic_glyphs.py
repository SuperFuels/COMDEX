from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Type, Union
def fallback_evaluate(glyph, env=None):
    from . import logic_glyph_evaluator  # ✅ local import
    return logic_glyph_evaluator.evaluate(glyph, env)

class LogicGlyph(ABC):
    def __init__(self, symbol: str, operands: List[Any], metadata: Optional[Dict[str, Any]] = None):
        self.symbol = symbol
        self.operands = operands
        self.metadata = metadata or {}

    @abstractmethod
    def evaluate(self, env: Optional[Dict[str, Any]] = None) -> Any:
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "symbol": self.symbol,
            "operands": [
                op.to_dict() if isinstance(op, LogicGlyph) else op for op in self.operands
            ],
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogicGlyph':
        glyph_cls = {
            "ImplicationGlyph": ImplicationGlyph,
            "AndGlyph": AndGlyph,
            "OrGlyph": OrGlyph,
            "NotGlyph": NotGlyph,
            "TrueGlyph": TrueGlyph,
            "FalseGlyph": FalseGlyph,
            "ProvableGlyph": ProvableGlyph,
            "EntailmentGlyph": EntailmentGlyph,
            "SequentGlyph": SequentGlyph,
            "ProofStepGlyph": ProofStepGlyph,
            "SymbolGlyph": SymbolGlyph,
        }.get(data["type"])

        if not glyph_cls:
            raise ValueError(f"Unknown glyph type: {data['type']}")

        operands = [
            LogicGlyph.from_dict(op) if isinstance(op, dict) else op
            for op in data.get("operands", [])
        ]
        metadata = data.get("metadata", {})

        # special cases: SymbolGlyph, TrueGlyph, etc.
        if glyph_cls == SymbolGlyph:
            return SymbolGlyph(data["symbol"])
        if glyph_cls in (TrueGlyph, FalseGlyph):
            return glyph_cls()
        if glyph_cls == SequentGlyph:
            return glyph_cls(operands[0], operands[1], rule_name=metadata.get("rule", ""))
        if glyph_cls == ProofStepGlyph:
            return glyph_cls(operands[0], operands[1], rule=metadata.get("rule", ""), notes=metadata.get("notes"))

        return glyph_cls(*operands)

    def __repr__(self):
        return f"{self.symbol}({', '.join(map(str, self.operands))})"


# Logical Connectives
class ImplicationGlyph(LogicGlyph):
    def __init__(self, premise, conclusion): super().__init__('→', [premise, conclusion])
    def evaluate(self, env: Optional[Dict[str, Any]] = None) -> bool:
        left = self.operands[0].evaluate(env) if isinstance(self.operands[0], LogicGlyph) else self.operands[0]
        right = self.operands[1].evaluate(env) if isinstance(self.operands[1], LogicGlyph) else self.operands[1]
        return (not left) or right


class AndGlyph(LogicGlyph):
    def __init__(self, left, right): super().__init__('∧', [left, right])
    def evaluate(self, env: Optional[Dict[str, Any]] = None) -> bool:
        left = self.operands[0].evaluate(env) if isinstance(self.operands[0], LogicGlyph) else self.operands[0]
        right = self.operands[1].evaluate(env) if isinstance(self.operands[1], LogicGlyph) else self.operands[1]
        return left and right


class OrGlyph(LogicGlyph):
    def __init__(self, left, right): super().__init__('∨', [left, right])
    def evaluate(self, env: Optional[Dict[str, Any]] = None) -> bool:
        left = self.operands[0].evaluate(env) if isinstance(self.operands[0], LogicGlyph) else self.operands[0]
        right = self.operands[1].evaluate(env) if isinstance(self.operands[1], LogicGlyph) else self.operands[1]
        return left or right


class NotGlyph(LogicGlyph):
    def __init__(self, operand): super().__init__('¬', [operand])
    def evaluate(self, env: Optional[Dict[str, Any]] = None) -> bool:
        operand = self.operands[0].evaluate(env) if isinstance(self.operands[0], LogicGlyph) else self.operands[0]
        return not operand


class TrueGlyph(LogicGlyph):
    def __init__(self): super().__init__('⊤', [])
    def evaluate(self, env: Optional[Dict[str, Any]] = None): return True


class FalseGlyph(LogicGlyph):
    def __init__(self): super().__init__('⊥', [])
    def evaluate(self, env: Optional[Dict[str, Any]] = None): return False


# Deduction Glyphs
class ProvableGlyph(LogicGlyph):  # ⊢
    def __init__(self, assumptions: List[Any], conclusion: Any):
        super().__init__('⊢', [assumptions, conclusion])
    def evaluate(self, env: Optional[Dict[str, Any]] = None): return f"{self.operands[0]} ⊢ {self.operands[1]}"


class EntailmentGlyph(LogicGlyph):  # ⊨
    def __init__(self, assumptions: List[Any], conclusion: Any):
        super().__init__('⊨', [assumptions, conclusion])
    def evaluate(self, env: Optional[Dict[str, Any]] = None): return f"{self.operands[0]} ⊨ {self.operands[1]}"


# Sequent Calculus Glyph
class SequentGlyph(LogicGlyph):
    def __init__(self, left: List[Any], right: List[Any], rule_name: str = ""):
        metadata = {"rule": rule_name}
        super().__init__('⊢', [left, right], metadata)
    def evaluate(self, env: Optional[Dict[str, Any]] = None):
        return f"{self.operands[0]} ⊢ {self.operands[1]} via {self.metadata.get('rule', 'unknown')}"


# Proof Tree Structure
class ProofStepGlyph(LogicGlyph):
    def __init__(self, premises: List[Any], conclusion: Any, rule: str = "", notes: Optional[str] = None):
        metadata = {"rule": rule, "notes": notes}
        super().__init__('⊢', [premises, conclusion], metadata)
    def evaluate(self, env: Optional[Dict[str, Any]] = None):
        return {
            "premises": self.operands[0],
            "conclusion": self.operands[1],
            "rule": self.metadata.get("rule"),
            "notes": self.metadata.get("notes"),
        }


# Atomic Symbol Glyph
class SymbolGlyph(LogicGlyph):
    def __init__(self, name: str): super().__init__(name, [])
    def evaluate(self, env: Optional[Dict[str, Any]] = None):
        if env is None:
            return False
        return env.get(self.symbol, False)
    def __repr__(self): return self.symbol


# Registry System
class LogicDomainRegistry:
    def __init__(self):
        self.registry: Dict[str, List[type]] = {}

    def register(self, domain: str, glyph_cls: type):
        if domain not in self.registry:
            self.registry[domain] = []
        self.registry[domain].append(glyph_cls)

    def get_domain(self, domain: str) -> List[type]:
        return self.registry.get(domain, [])


# Singleton for SQI/Codex use
logic_registry = LogicDomainRegistry()
logic_registry.register("classical", ImplicationGlyph)
logic_registry.register("classical", AndGlyph)
logic_registry.register("classical", OrGlyph)
logic_registry.register("classical", NotGlyph)
logic_registry.register("classical", TrueGlyph)
logic_registry.register("classical", FalseGlyph)
logic_registry.register("classical", SymbolGlyph)
logic_registry.register("deduction", ProvableGlyph)
logic_registry.register("deduction", EntailmentGlyph)
logic_registry.register("sequent", SequentGlyph)
logic_registry.register("proof", ProofStepGlyph)


# Expression Tree Composer (Preview for GHX/CodexLang)
def compose_logic_tree(glyphs: List[LogicGlyph]) -> str:
    return ' ⇒ '.join(map(str, glyphs))