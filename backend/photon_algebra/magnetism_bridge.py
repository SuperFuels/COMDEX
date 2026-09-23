from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from backend.photon_algebra.rewriter import normalize
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_field_compiler import (
    FieldEmissionProgram,
    SymaticsFieldCompiler,
)


@dataclass(slots=True)
class MagneticIntent:
    mode: str
    phi_bias: float = 0.0
    harmonic_bias: List[int] = field(default_factory=list)
    coherence_target: float = 0.0
    rotational_memory_target: float = 0.0
    coupling_target: float = 0.0
    containment_target: float = 0.0
    preferred_symbol_id: Optional[str] = None
    notes: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PhotonFieldIntent:
    source_expr: Any
    normalized_expr: Any
    semantic_label: str
    symbol_hint: Optional[str]
    magnetic_intent: MagneticIntent
    notes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PhotonMagnetismBridge:
    def __init__(self, symatics_catalog_path: str | None = None):
        self.symatics = (
            SymaticsFieldCompiler(symatics_catalog_path)
            if symatics_catalog_path
            else None
        )

    def _collect_atomic_terms(self, expr: Any) -> List[str]:
        out: List[str] = []

        def walk(node: Any) -> None:
            if isinstance(node, str):
                out.append(node)
                return
            if isinstance(node, dict):
                if "state" in node:
                    walk(node["state"])
                for s in node.get("states", []):
                    walk(s)

        walk(expr)
        return out

    def _infer_semantic_intent(
        self,
        norm: Any,
    ) -> Tuple[str, Optional[str], MagneticIntent]:
        semantic_label = "unknown"
        symbol_hint: Optional[str] = None
        magnetic_intent = MagneticIntent(mode="passive")

        if not isinstance(norm, dict):
            return semantic_label, symbol_hint, magnetic_intent

        op = norm.get("op")
        states = norm.get("states", [])
        state = norm.get("state")

        if op == "↔":
            semantic_label = "entangled_alignment"
            symbol_hint = "S2"
            magnetic_intent = MagneticIntent(
                mode="coupled_alignment",
                phi_bias=1.5707963267948966,
                harmonic_bias=[1, 2],
                coherence_target=0.8,
                rotational_memory_target=0.7,
                coupling_target=0.9,
                containment_target=0.0,
                preferred_symbol_id="S2",
                notes={
                    "reason": "entanglement-like normalized form",
                    "operator": "↔",
                },
            )
            return semantic_label, symbol_hint, magnetic_intent

        if op == "⊗_M":
            semantic_label = "magnetically_coupled_field"
            symbol_hint = "S2"
            magnetic_intent = MagneticIntent(
                mode="magnetic_coupling",
                phi_bias=1.5707963267948966,
                harmonic_bias=[1, 2],
                coherence_target=0.8,
                rotational_memory_target=0.85,
                coupling_target=0.95,
                containment_target=0.4,
                preferred_symbol_id="S2",
                notes={
                    "reason": "explicit magnetic coupling/composition structure",
                    "operator": "⊗_M",
                },
            )
            return semantic_label, symbol_hint, magnetic_intent

        if op == "⊗":
            semantic_label = "fused_field"
            symbol_hint = "S1"
            magnetic_intent = MagneticIntent(
                mode="constructive_lock",
                phi_bias=0.0,
                harmonic_bias=[1, 2],
                coherence_target=0.7,
                rotational_memory_target=0.6,
                coupling_target=0.0,
                containment_target=0.7,
                preferred_symbol_id="S1",
                notes={
                    "reason": "product/fusion normalized form",
                    "operator": "⊗",
                },
            )
            return semantic_label, symbol_hint, magnetic_intent

        if op == "⊕":
            has_neg = any(isinstance(s, dict) and s.get("op") == "¬" for s in states)
            has_cancel = any(isinstance(s, dict) and s.get("op") == "⊖" for s in states)

            if has_neg or has_cancel:
                semantic_label = "superposed_anti_alignment"
                symbol_hint = "S4"
                magnetic_intent = MagneticIntent(
                    mode="destructive_distribution",
                    phi_bias=4.71238898038469,
                    harmonic_bias=[1],
                    coherence_target=0.5,
                    rotational_memory_target=0.4,
                    coupling_target=0.0,
                    containment_target=0.0,
                    preferred_symbol_id="S4",
                    notes={
                        "reason": "sum contains negation/cancellation structure",
                        "operator": "⊕",
                    },
                )
            else:
                semantic_label = "superposed_field"
                symbol_hint = None
                magnetic_intent = MagneticIntent(
                    mode="distributed_interference",
                    phi_bias=0.0,
                    harmonic_bias=[],
                    coherence_target=0.5,
                    rotational_memory_target=0.4,
                    coupling_target=0.0,
                    containment_target=0.0,
                    preferred_symbol_id="S1",
                    notes={
                        "reason": "plain superposition normalized form",
                        "operator": "⊕",
                    },
                )

            return semantic_label, symbol_hint, magnetic_intent

        if op == "Φ_B":
            semantic_label = "magnetic_state_field"
            symbol_hint = "S2"
            magnetic_intent = MagneticIntent(
                mode="magnetic_state_encoding",
                phi_bias=1.5707963267948966,
                harmonic_bias=[1, 2],
                coherence_target=0.75,
                rotational_memory_target=0.9,
                coupling_target=0.6,
                containment_target=0.3,
                preferred_symbol_id="S2",
                notes={
                    "reason": "explicit magnetic-state operator",
                    "operator": "Φ_B",
                    "inner_state": state,
                },
            )
            return semantic_label, symbol_hint, magnetic_intent

        if op == "¬":
            semantic_label = "negated_field"
            symbol_hint = "S4"
            magnetic_intent = MagneticIntent(
                mode="anti_alignment",
                phi_bias=4.71238898038469,
                harmonic_bias=[1],
                coherence_target=0.5,
                rotational_memory_target=0.7,
                coupling_target=0.0,
                containment_target=0.0,
                preferred_symbol_id="S4",
                notes={
                    "reason": "negation structure",
                    "operator": "¬",
                },
            )
            return semantic_label, symbol_hint, magnetic_intent

        if op == "⊖":
            semantic_label = "cancellation_field"
            symbol_hint = "S4"
            magnetic_intent = MagneticIntent(
                mode="field_cancellation",
                phi_bias=4.71238898038469,
                harmonic_bias=[1],
                coherence_target=0.5,
                rotational_memory_target=0.7,
                coupling_target=0.0,
                containment_target=0.0,
                preferred_symbol_id="S4",
                notes={
                    "reason": "difference/cancellation structure",
                    "operator": "⊖",
                },
            )
            return semantic_label, symbol_hint, magnetic_intent

        if op == "★":
            semantic_label = "projected_field"
            symbol_hint = "S1"
            magnetic_intent = MagneticIntent(
                mode="measurement_projection",
                phi_bias=0.0,
                harmonic_bias=[1],
                coherence_target=0.5,
                rotational_memory_target=0.3,
                coupling_target=0.0,
                containment_target=0.0,
                preferred_symbol_id="S1",
                notes={
                    "reason": "projection structure",
                    "operator": "★",
                },
            )
            return semantic_label, symbol_hint, magnetic_intent

        return semantic_label, symbol_hint, magnetic_intent

    def compile_expr(self, expr: Any) -> PhotonFieldIntent:
        norm = normalize(expr)
        semantic_label, symbol_hint, magnetic_intent = self._infer_semantic_intent(norm)

        return PhotonFieldIntent(
            source_expr=expr,
            normalized_expr=norm,
            semantic_label=semantic_label,
            symbol_hint=symbol_hint,
            magnetic_intent=magnetic_intent,
            notes={
                "bridge": "PhotonMagnetismBridge",
                "atomic_terms": self._collect_atomic_terms(norm),
            },
        )

    def compile_to_symatics_program(
        self,
        expr: Any,
        *,
        fallback_symbol_id: str = "S1",
        amplitude: float = 1.0,
        frequency: float = 1.0,
        duty_cycle: float = 0.5,
        envelope: str = "steady",
    ) -> tuple[PhotonFieldIntent, FieldEmissionProgram]:
        if self.symatics is None:
            raise RuntimeError("SymaticsFieldCompiler not configured")

        intent = self.compile_expr(expr)

        symbol_id = (
            intent.symbol_hint
            or intent.magnetic_intent.preferred_symbol_id
            or fallback_symbol_id
        )

        program = self.symatics.compile_symbol(
            symbol_id,
            amplitude=amplitude,
            frequency=frequency,
            duty_cycle=duty_cycle,
            envelope=envelope,
            metadata={
                "source": "PhotonMagnetismBridge",
                "semantic_label": intent.semantic_label,
                "magnetic_mode": intent.magnetic_intent.mode,
                "phi_bias": intent.magnetic_intent.phi_bias,
                "harmonic_bias": list(intent.magnetic_intent.harmonic_bias),
                "coherence_target": intent.magnetic_intent.coherence_target,
                "rotational_memory_target": intent.magnetic_intent.rotational_memory_target,
                "coupling_target": intent.magnetic_intent.coupling_target,
                "containment_target": intent.magnetic_intent.containment_target,
                "normalized_expr": intent.normalized_expr,
                "bridge_notes": dict(intent.magnetic_intent.notes),
            },
        )
        return intent, program