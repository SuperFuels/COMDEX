from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class AionSymaticsStateAdapter:
    """
    Normalize Symatics / field-sim output into one HexCore-readable packet.

    Non-breaking design:
    - accepts partial inputs
    - never throws intentionally
    - preserves raw metrics under `raw`
    - preserves canonical symatics fields under `symatics`
    - supports multiple alias names from qwave / Symatics runners
    - normalizes sentinel / bogus drift values
    - recomputes entropy when raw entropy is clearly inconsistent
    """

    FIELD_ALIASES = {
        "S1": ("S1", "s1"),
        "S2": ("S2", "s2"),
        "S4": ("S4", "s4"),
        "E": ("E", "e", "energy"),
        "H": ("H", "h", "harmonic", "harmonic_value"),
        "resonance": ("resonance", "R", "res_coh", "resonance_coherence"),
        "coherence": ("coherence", "C", "phase_coherence", "res_coh"),
        "entropy": ("entropy", "psi", "Ψ", "pickup_norm", "pickup"),
        "delta_phi": ("delta_phi", "dphi", "drift", "phase_drift"),
        "self_awareness": ("self_awareness", "S_self", "s_self"),
        "global_coherence": ("global_coherence", "global_coherence_score"),
        "phase": ("phase", "phi"),
        "frequency": ("frequency", "freq", "f"),
        "amplitude": ("amplitude", "amp", "A"),
        "tick_count": ("tick_count", "ticks"),
        "observed_regime": ("observed_regime", "regime"),
        "predicted_symbol": ("predicted_symbol", "symbol", "symbol_id"),
        "locked": ("locked", "is_locked"),
        "drift_raw": ("drift",),
    }

    DRIFT_SENTINEL_THRESHOLD = 10.0

    @classmethod
    def _pick_float(
        cls,
        raw: Mapping[str, Any],
        *names: str,
        default: float = 0.0,
    ) -> float:
        for name in names:
            if name in raw:
                return _safe_float(raw.get(name), default)
        return float(default)

    @classmethod
    def _pick_any(
        cls,
        raw: Mapping[str, Any],
        *names: str,
        default: Any = None,
    ) -> Any:
        for name in names:
            if name in raw:
                return raw.get(name)
        return default

    @classmethod
    def _pick_bool(
        cls,
        raw: Mapping[str, Any],
        *names: str,
        default: bool = False,
    ) -> bool:
        value = cls._pick_any(raw, *names, default=default)
        if isinstance(value, bool):
            return value
        if value is None:
            return bool(default)
        if isinstance(value, (int, float)):
            return bool(value)
        return str(value).strip().lower() in {"1", "true", "yes", "on", "locked"}

    @classmethod
    def _extract_symbol_strengths(cls, raw: Mapping[str, Any]) -> Dict[str, float]:
        return {
            "S1": cls._pick_float(raw, *cls.FIELD_ALIASES["S1"], default=0.0),
            "S2": cls._pick_float(raw, *cls.FIELD_ALIASES["S2"], default=0.0),
            "S4": cls._pick_float(raw, *cls.FIELD_ALIASES["S4"], default=0.0),
        }

    @classmethod
    def _normalize_drift(
        cls,
        raw: Mapping[str, Any],
        *,
        delta_phi_raw: float,
    ) -> float:
        raw_drift = cls._pick_float(raw, *cls.FIELD_ALIASES["drift_raw"], default=delta_phi_raw)

        if raw_drift > cls.DRIFT_SENTINEL_THRESHOLD:
            raw_drift = delta_phi_raw

        return _clamp(abs(raw_drift), 0.0, 1.0)

    @classmethod
    def _derive_entropy(
        cls,
        raw: Mapping[str, Any],
        *,
        s4: float,
        coherence_n: float,
    ) -> float:
        if any(name in raw for name in cls.FIELD_ALIASES["entropy"]):
            entropy_raw = cls._pick_float(raw, *cls.FIELD_ALIASES["entropy"], default=s4)
            entropy_n = _clamp(entropy_raw, 0.0, 1.0)

            # Raw entropy is clearly inconsistent with a strongly coherent live field.
            if entropy_n >= 0.999 and coherence_n > 0.9:
                return _clamp(1.0 - coherence_n, 0.0, 1.0)

            return entropy_n

        entropy_proxy = (0.65 * _clamp(s4, 0.0, 1.0)) + (0.35 * (1.0 - coherence_n))
        return _clamp(entropy_proxy, 0.0, 1.0)

    @classmethod
    def _derive_self_awareness(
        cls,
        raw: Mapping[str, Any],
        *,
        coherence_n: float,
        resonance_n: float,
        drift_n: float,
        s1: float,
        s2: float,
    ) -> float:
        if any(name in raw for name in cls.FIELD_ALIASES["self_awareness"]):
            direct = cls._pick_float(raw, *cls.FIELD_ALIASES["self_awareness"], default=0.0)
            return _clamp(direct, 0.0, 1.0)

        constructive_bias = _clamp((s1 + (0.5 * s2)) / 1.5, 0.0, 1.0)
        s_self_proxy = (
            (0.35 * coherence_n)
            + (0.25 * resonance_n)
            + (0.25 * (1.0 - drift_n))
            + (0.15 * constructive_bias)
        )
        return _clamp(s_self_proxy, 0.0, 1.0)

    @classmethod
    def _derive_global_coherence(
        cls,
        raw: Mapping[str, Any],
        *,
        coherence_n: float,
        resonance_n: float,
        entropy_n: float,
        drift_n: float,
        s1: float,
        s2: float,
        s4: float,
    ) -> float:
        if any(name in raw for name in cls.FIELD_ALIASES["global_coherence"]):
            direct = cls._pick_float(raw, *cls.FIELD_ALIASES["global_coherence"], default=coherence_n)
            return _clamp(direct, 0.0, 1.0)

        symbolic_constructive = _clamp((s1 + s2) / 2.0 if (s1 or s2) else coherence_n, 0.0, 1.0)
        symbolic_drag = _clamp(s4, 0.0, 1.0)

        global_coherence = (
            (0.32 * coherence_n)
            + (0.22 * resonance_n)
            + (0.18 * (1.0 - entropy_n))
            + (0.14 * (1.0 - drift_n))
            + (0.14 * symbolic_constructive)
            - (0.08 * symbolic_drag)
        )
        return _clamp(global_coherence, 0.0, 1.0)

    @classmethod
    def adapt(cls, state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        raw: Dict[str, Any] = dict(state or {})

        symbols = cls._extract_symbol_strengths(raw)
        s1 = _clamp(symbols["S1"], 0.0, 1.0)
        s2 = _clamp(symbols["S2"], 0.0, 1.0)
        s4 = _clamp(symbols["S4"], 0.0, 1.0)

        e = cls._pick_float(raw, *cls.FIELD_ALIASES["E"], default=0.0)
        h = cls._pick_float(raw, *cls.FIELD_ALIASES["H"], default=0.0)

        resonance_raw = cls._pick_float(raw, *cls.FIELD_ALIASES["resonance"], default=0.0)
        coherence_raw = cls._pick_float(raw, *cls.FIELD_ALIASES["coherence"], default=0.0)
        delta_phi_raw = cls._pick_float(raw, *cls.FIELD_ALIASES["delta_phi"], default=0.0)

        coherence_n = _clamp(coherence_raw, 0.0, 1.0)
        resonance_n = _clamp(resonance_raw, 0.0, 1.0)
        drift_n = cls._normalize_drift(raw, delta_phi_raw=delta_phi_raw)

        entropy_n = cls._derive_entropy(raw, s4=s4, coherence_n=coherence_n)
        self_awareness_n = cls._derive_self_awareness(
            raw,
            coherence_n=coherence_n,
            resonance_n=resonance_n,
            drift_n=drift_n,
            s1=s1,
            s2=s2,
        )
        global_coherence_n = cls._derive_global_coherence(
            raw,
            coherence_n=coherence_n,
            resonance_n=resonance_n,
            entropy_n=entropy_n,
            drift_n=drift_n,
            s1=s1,
            s2=s2,
            s4=s4,
        )

        dominant_symbol = max(
            (("S1", s1), ("S2", s2), ("S4", s4)),
            key=lambda item: item[1],
        )[0]

        phase = cls._pick_float(raw, *cls.FIELD_ALIASES["phase"], default=0.0)
        frequency = cls._pick_float(raw, *cls.FIELD_ALIASES["frequency"], default=0.0)
        amplitude = cls._pick_float(raw, *cls.FIELD_ALIASES["amplitude"], default=e)

        tick_count = int(cls._pick_float(raw, *cls.FIELD_ALIASES["tick_count"], default=0.0))
        observed_regime = str(cls._pick_any(raw, *cls.FIELD_ALIASES["observed_regime"], default="unknown"))
        predicted_symbol = cls._pick_any(raw, *cls.FIELD_ALIASES["predicted_symbol"], default=None)
        locked = cls._pick_bool(raw, *cls.FIELD_ALIASES["locked"], default=False)

        return {
            "coherence": coherence_n,
            "delta_phi": drift_n,
            "entropy": entropy_n,
            "self_awareness": self_awareness_n,
            "global_coherence": global_coherence_n,
            "symatics": {
                "S1": s1,
                "S2": s2,
                "S4": s4,
                "E": e,
                "H": h,
                "resonance": resonance_n,
                "dominant_symbol": dominant_symbol,
            },
            "raw": raw,
            "tick_count": tick_count,
            "observed_regime": observed_regime,
            "predicted_symbol": predicted_symbol,
            "locked": locked,
            "phase": phase,
            "frequency": frequency,
            "amplitude": amplitude,
        }