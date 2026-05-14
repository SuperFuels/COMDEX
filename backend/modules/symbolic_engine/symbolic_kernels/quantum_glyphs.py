from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class QuantumGlyph(ABC):
    def __init__(self, symbol: str, operands: List[Any], metadata: Optional[Dict[str, Any]] = None):
        self.symbol = symbol
        self.operands = operands
        self.metadata = metadata or {}

    @abstractmethod
    def evaluate(self):
        pass

    def __repr__(self):
        return f"{self.symbol}({', '.join(map(str, self.operands))})"


# 🧬 QBit representation
class QBitGlyph(QuantumGlyph):
    def __init__(self, label: str, state: str = "|0⟩"):
        metadata = {"state": state}
        super().__init__('🧬', [label], metadata)
    def evaluate(self): return {"qbit": self.operands[0], "state": self.metadata["state"]}


# ↔ Entanglement link
class EntanglementGlyph(QuantumGlyph):
    def __init__(self, left: Any, right: Any):
        super().__init__('↔', [left, right])
    def evaluate(self): return {"entangled": (self.operands[0], self.operands[1])}


# ⚛ Superposition (|ψ⟩ = α|0⟩ + β|1⟩)
class SuperpositionGlyph(QuantumGlyph):
    def __init__(self, label: str, amplitudes: Dict[str, float]):
        metadata = {"amplitudes": amplitudes}
        super().__init__('⚛', [label], metadata)
    def evaluate(self): return {"superposition": self.operands[0], "amplitudes": self.metadata["amplitudes"]}


# ⧖ Collapse event
class CollapseGlyph(QuantumGlyph):
    def __init__(self, input_state: Any, result_state: Any, cause: Optional[str] = None):
        metadata = {"cause": cause}
        super().__init__('⧖', [input_state, result_state], metadata)
    def evaluate(self): return {
        "collapse": {"from": self.operands[0], "to": self.operands[1]},
        "cause": self.metadata.get("cause", "observation")
    }


# Quantum Gate (e.g., H, X, CNOT)
class QuantumGateGlyph(QuantumGlyph):
    def __init__(self, gate: str, targets: List[str]):
        metadata = {"gate": gate}
        super().__init__('🌀', targets, metadata)
    def evaluate(self): return {"gate": self.metadata["gate"], "targets": self.operands}


# Quantum Measurement (⟨ψ|O|ψ⟩)
class MeasurementGlyph(QuantumGlyph):
    def __init__(self, qbit: str, observable: str):
        metadata = {"observable": observable}
        super().__init__('🧭', [qbit], metadata)
    def evaluate(self): return {"measure": self.operands[0], "observable": self.metadata["observable"]}


# Registry
class QuantumDomainRegistry:
    def __init__(self):
        self.registry: Dict[str, List[type]] = {}

    def register(self, domain: str, glyph_cls: type):
        if domain not in self.registry:
            self.registry[domain] = []
        self.registry[domain].append(glyph_cls)

    def get_domain(self, domain: str) -> List[type]:
        return self.registry.get(domain, [])


# Singleton Registry for Codex/SQI
quantum_registry = QuantumDomainRegistry()
quantum_registry.register("qbits", QBitGlyph)
quantum_registry.register("qbits", EntanglementGlyph)
quantum_registry.register("qbits", SuperpositionGlyph)
quantum_registry.register("qbits", CollapseGlyph)
quantum_registry.register("gates", QuantumGateGlyph)
quantum_registry.register("gates", MeasurementGlyph)