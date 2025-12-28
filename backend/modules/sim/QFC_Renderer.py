from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple


# ----------------------------
# Utilities
# ----------------------------

def clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def num(v: Any, d: float = 0.0) -> float:
    try:
        x = float(v)
        if x != x:  # NaN
            return d
        return x
    except Exception:
        return d


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def smoothstep(t: float) -> float:
    t = clamp01(t)
    return t * t * (3.0 - 2.0 * t)


def parse_rgba(s: str) -> Tuple[float, float, float, float]:
    # expects "rgba(r,g,b,a)"
    s = (s or "").strip()
    if not s.startswith("rgba"):
        raise ValueError(f"Expected rgba(...), got: {s}")
    inner = s[s.find("(") + 1 : s.rfind(")")]
    parts = [p.strip() for p in inner.split(",")]
    if len(parts) != 4:
        raise ValueError(f"Bad rgba: {s}")
    r, g, b = float(parts[0]), float(parts[1]), float(parts[2])
    a = float(parts[3])
    return r, g, b, a


def fmt_rgba(r: float, g: float, b: float, a: float) -> str:
    r = int(max(0, min(255, round(r))))
    g = int(max(0, min(255, round(g))))
    b = int(max(0, min(255, round(b))))
    a = max(0.0, min(1.0, a))
    return f"rgba({r},{g},{b},{a:.3f})"


def mix_rgba(a: str, b: str, t: float) -> str:
    ar, ag, ab, aa = parse_rgba(a)
    br, bg, bb, ba = parse_rgba(b)
    t = clamp01(t)
    return fmt_rgba(
        lerp(ar, br, t),
        lerp(ag, bg, t),
        lerp(ab, bb, t),
        lerp(aa, ba, t),
    )


# ----------------------------
# Theme / palette model
# ----------------------------

@dataclass
class QFCTheme:
    gravity: str = "rgba(56,189,248,0.65)"     # cobalt/blue
    matter: str = "rgba(226,232,240,0.75)"     # silver/grey
    photon: str = "rgba(251,191,36,0.70)"      # amber/gold
    connect: str = "rgba(34,211,238,0.70)"     # cyan
    danger: str = "rgba(239,68,68,0.80)"       # red
    antigrav: str = "rgba(34,197,94,0.75)"     # emerald
    sync: str = "rgba(216,180,254,0.75)"       # violet


@dataclass
class RenderFlags:
    nec_violation: bool = False
    nec_strength: float = 0.0         # 0..1
    jump_flash: float = 0.0           # 0..1


@dataclass
class QFCFrameOut:
    t: float
    mode: str                         # gravity|matter|tunnel|connect|antigrav|sync
    theme: Dict[str, str]             # rgba strings
    flags: Dict[str, Any]

    # typical metrics (passthrough)
    kappa: float = 0.0
    chi: float = 0.0
    sigma: float = 0.0
    alpha: float = 0.0
    curl_rms: float = 0.0
    curv: float = 0.0
    coupling_score: float = 0.0
    max_norm: float = 0.0


# ----------------------------
# Force-color mapping
# ----------------------------

FORCE_PALETTE: Dict[str, Dict[str, str]] = {
    "gravity": {
        "gravity": "rgba(56,189,248,0.70)",
        "matter":  "rgba(226,232,240,0.55)",
        "photon":  "rgba(251,191,36,0.35)",
        "connect": "rgba(34,211,238,0.45)",
        "danger":  "rgba(239,68,68,0.40)",
        "antigrav":"rgba(34,197,94,0.35)",
        "sync":    "rgba(216,180,254,0.35)",
    },
    "matter": {
        "gravity": "rgba(56,189,248,0.40)",
        "matter":  "rgba(226,232,240,0.85)",
        "photon":  "rgba(251,191,36,0.25)",
        "connect": "rgba(34,211,238,0.30)",
        "danger":  "rgba(239,68,68,0.25)",
        "antigrav":"rgba(34,197,94,0.25)",
        "sync":    "rgba(216,180,254,0.25)",
    },
    "tunnel": {
        "gravity": "rgba(56,189,248,0.25)",
        "matter":  "rgba(226,232,240,0.35)",
        "photon":  "rgba(251,191,36,0.82)",
        "connect": "rgba(34,211,238,0.35)",
        "danger":  "rgba(239,68,68,0.88)",
        "antigrav":"rgba(34,197,94,0.25)",
        "sync":    "rgba(216,180,254,0.25)",
    },
    "connect": {
        "gravity": "rgba(56,189,248,0.30)",
        "matter":  "rgba(226,232,240,0.35)",
        "photon":  "rgba(251,191,36,0.25)",
        "connect": "rgba(34,211,238,0.88)",
        "danger":  "rgba(239,68,68,0.30)",
        "antigrav":"rgba(34,197,94,0.30)",
        "sync":    "rgba(216,180,254,0.30)",
    },
    "antigrav": {
        "gravity": "rgba(56,189,248,0.25)",
        "matter":  "rgba(226,232,240,0.30)",
        "photon":  "rgba(251,191,36,0.25)",
        "connect": "rgba(34,211,238,0.35)",
        "danger":  "rgba(239,68,68,0.35)",
        "antigrav":"rgba(34,197,94,0.92)",
        "sync":    "rgba(216,180,254,0.30)",
    },
    "sync": {
        "gravity": "rgba(56,189,248,0.25)",
        "matter":  "rgba(226,232,240,0.25)",
        "photon":  "rgba(251,191,36,0.25)",
        "connect": "rgba(34,211,238,0.25)",
        "danger":  "rgba(239,68,68,0.25)",
        "antigrav":"rgba(34,197,94,0.25)",
        "sync":    "rgba(255,255,255,0.88)",
    },
}


def scenario_to_mode(scenario_id: str, fallback: str = "gravity") -> str:
    s = (scenario_id or "").upper()
    if s.startswith("TN"):
        return "tunnel"
    if s.startswith("MT"):
        return "matter"
    if s.startswith("C"):
        return "connect"
    if s.startswith("A"):
        return "antigrav"
    if s.startswith("SYNC") or s.startswith("H"):
        return "sync"
    if s.startswith("G"):
        return "gravity"
    return fallback


# ----------------------------
# Main renderer state
# ----------------------------

class QFCRenderer:
    """
    Call update(...) once per sim tick and stream the returned dict.
    Keeps internal state for smooth palette transitions + event pulses.
    """

    def __init__(self) -> None:
        self._theme = QFCTheme()
        self._target_theme = QFCTheme()
        self._mode: str = "gravity"
        self._prev_coupling: Optional[float] = None
        self._jump_flash: float = 0.0
        self._nec_strength: float = 0.0
        self._set_target_palette(self._mode)

    def _set_target_palette(self, mode: str) -> None:
        pal = FORCE_PALETTE.get(mode, FORCE_PALETTE["gravity"])
        self._target_theme = QFCTheme(
            gravity=pal["gravity"],
            matter=pal["matter"],
            photon=pal["photon"],
            connect=pal["connect"],
            danger=pal["danger"],
            antigrav=pal["antigrav"],
            sync=pal["sync"],
        )

    def _transition_theme(self, dt: float) -> None:
        # dt in seconds; ~0.18s time constant
        tau = 0.18
        if dt <= 0:
            return
        t = 1.0 - pow(2.718281828, -dt / tau)
        t = smoothstep(t)

        self._theme.gravity = mix_rgba(self._theme.gravity, self._target_theme.gravity, t)
        self._theme.matter  = mix_rgba(self._theme.matter,  self._target_theme.matter,  t)
        self._theme.photon  = mix_rgba(self._theme.photon,  self._target_theme.photon,  t)
        self._theme.connect = mix_rgba(self._theme.connect, self._target_theme.connect, t)
        self._theme.danger  = mix_rgba(self._theme.danger,  self._target_theme.danger,  t)
        self._theme.antigrav= mix_rgba(self._theme.antigrav,self._target_theme.antigrav,t)
        self._theme.sync    = mix_rgba(self._theme.sync,    self._target_theme.sync,    t)

    def _update_jump_flash(self, coupling: float, dt: float) -> None:
        if self._prev_coupling is None:
            self._prev_coupling = coupling
            return

        delta = abs(coupling - self._prev_coupling)
        self._prev_coupling = coupling

        if delta > 0.10:
            self._jump_flash = 1.0

        decay = 6.5  # per second
        self._jump_flash = max(0.0, self._jump_flash - decay * max(0.0, dt))

    def _update_nec(self, kappa: float, alpha: float, curv: float, coupling: float, dt: float) -> None:
        """
        NEC heuristic (replace with your true NEC metric when available).
        """
        raw = 0.0
        raw += clamp01((kappa - 0.65) / 0.25) * 0.45
        raw += clamp01((alpha - 0.55) / 0.30) * 0.35
        raw += clamp01((coupling - 0.60) / 0.25) * 0.25
        raw -= clamp01((curv - 0.10) / 0.20) * 0.35
        raw = clamp01(raw)

        tau = 0.22
        if dt <= 0:
            return
        t = 1.0 - pow(2.718281828, -dt / tau)
        self._nec_strength = lerp(self._nec_strength, raw, t)

    def update(
        self,
        *,
        t: float,
        scenario_id: str,
        metrics: Dict[str, Any],
        dt: float,
        mode_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        kappa = clamp01(num(metrics.get("kappa"), 0.12))
        chi = clamp01(num(metrics.get("chi"), 0.22))
        sigma = clamp01(num(metrics.get("sigma"), 0.55))
        alpha = clamp01(num(metrics.get("alpha"), 0.12))
        curv = clamp01(num(metrics.get("curv"), 0.18))
        curl_rms = max(0.0, num(metrics.get("curl_rms"), 0.03))
        coupling = clamp01(num(metrics.get("coupling_score"), 0.55))
        max_norm = max(0.0, num(metrics.get("max_norm"), 0.0))

        mode = (mode_hint or "").strip().lower() or scenario_to_mode(scenario_id, fallback=self._mode)
        if mode != self._mode:
            self._mode = mode
            self._set_target_palette(mode)

        self._transition_theme(dt)
        self._update_jump_flash(coupling, dt)
        self._update_nec(kappa, alpha, curv, coupling, dt)

        flags = RenderFlags(
            nec_violation=(self._nec_strength > 0.62),
            nec_strength=float(self._nec_strength),
            jump_flash=float(self._jump_flash),
        )

        out = QFCFrameOut(
            t=float(t),
            mode=self._mode,
            theme=asdict(self._theme),
            flags=asdict(flags),
            kappa=kappa,
            chi=chi,
            sigma=sigma,
            alpha=alpha,
            curl_rms=float(curl_rms),
            curv=curv,
            coupling_score=coupling,
            max_norm=float(max_norm),
        )

        return asdict(out)