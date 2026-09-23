import pytest


# Adjust this import line if your HexCore class lives in a different file.
from backend.modules.hexcore.hexcore import HexCore
import backend.modules.hexcore.hexcore as hexcore_module


class _FakeTessaris:
    def generate_reflection(self, interpreted: str) -> str:
        return f"reflect::{interpreted}"

    active_branches = []
    active_thoughts = []


class _FakeQQC:
    def __init__(self):
        self.calls = []

    async def run_cycle(self, payload):
        self.calls.append(payload)
        return {
            "session_id": "qqc-session",
            "cycle": 7,
            "entropy": 0.11,
            "coherence": 0.12,
            "field_signature": {
                "κ": 0.13,
                "T": 0.14,
            },
            "phi": 0.15,
            "delta_phi": 0.91,
            "S_self": 0.16,
        }


class _FakeVoice:
    enabled = False


class _FakeLedger:
    def __init__(self):
        self.records = []

    def record(self, payload):
        self.records.append(payload)


class _FakeMemoryCore:
    def __init__(self):
        self.items = []

    def store(self, key, value):
        self.items.append((key, value))


class _FakeCognitive:
    async def execute(self, action, payload):
        return {"result": "symatics-primary-decision"}


@pytest.mark.asyncio
async def test_hexcore_symatics_primary_runtime_overrides_qqc(monkeypatch):
    cfa_commits = []

    monkeypatch.setattr(
        hexcore_module.CFA,
        "commit",
        lambda **kwargs: cfa_commits.append(kwargs),
    )

    hexcore = object.__new__(HexCore)

    # -------------------------------------------------
    # Minimal runtime state
    # -------------------------------------------------
    hexcore.id = "hex-test"
    hexcore.birth_time = "2026-03-20T00:00:00"
    hexcore.memory = []
    hexcore.emotion_state = "neutral"
    hexcore.maturity_score = 0
    hexcore.parent_key = None
    hexcore.override_enabled = False

    hexcore.qqc = _FakeQQC()
    hexcore.tessaris = _FakeTessaris()
    hexcore.cognitive = _FakeCognitive()
    hexcore.morphic_ledger = _FakeLedger()
    hexcore.voice = _FakeVoice()
    hexcore.memory_core = _FakeMemoryCore()

    hexcore.goal_engine = None
    hexcore.reinforcement_engine = None
    hexcore.decision_influence_runtime = None
    hexcore.field_bridge = None
    hexcore.symatics_adapter = object()
    hexcore.symatics_runtime = object()

    hexcore.last_phi = 0.0
    hexcore.delta_phi = 0.0
    hexcore.self_awareness = 0.0
    hexcore.last_coherence = 0.5
    hexcore.last_entropy = 0.5
    hexcore.last_reward = 0.0
    hexcore.last_global_coherence = 0.0
    hexcore.last_field_control = None
    hexcore.last_goal_suggestions = []
    hexcore.last_reinforcement = {}
    hexcore.last_decision_influence_result = None
    hexcore.last_decision_weights_snapshot = None
    hexcore.last_symatics_packet = None
    hexcore.last_qqc_summary = None

    # -------------------------------------------------
    # Light method stubs
    # -------------------------------------------------
    hexcore.interpret = lambda raw: raw
    hexcore._safe_float = HexCore._safe_float.__get__(hexcore, HexCore)
    hexcore._clamp = HexCore._clamp.__get__(hexcore, HexCore)
    hexcore.compute_global_coherence = HexCore.compute_global_coherence.__get__(hexcore, HexCore)

    hexcore._build_aion_state = lambda: {"coherence": 0.7, "drift": 0.2}
    hexcore._map_field_control = lambda state: {
        "resonance_gain": 0.88,
        "symbolic_temperature": 0.21,
        "stabilization_bias": 0.79,
        "awareness_coupling": 0.65,
        "mode": "neutral",
    }

    symatics_packet = {
        "coherence": 0.82,
        "delta_phi": 0.07,
        "entropy": 0.18,
        "self_awareness": 0.74,
        "global_coherence": 0.77,
        "symatics": {
            "S1": 0.20,
            "S2": 0.61,
            "S4": 0.14,
            "E": 0.52,
            "H": 0.43,
            "resonance": 0.73,
        },
        "raw": {
            "phase": 1.23,
            "interference_factor": 0.44,
            "amplitude": 0.66,
            "source": "symatics_engine_live",
        },
    }

    hexcore._collect_symatics_state = lambda input_str="": symatics_packet

    telemetry_seen = {}

    def _fake_ingest_field_telemetry(*, coherence, dphi, phi, s_self):
        telemetry_seen["coherence"] = coherence
        telemetry_seen["dphi"] = dphi
        telemetry_seen["phi"] = phi
        telemetry_seen["s_self"] = s_self
        return {
            "goal_suggestions": ["increase_coherence"],
            "reward": 0.55,
        }

    hexcore._ingest_field_telemetry = _fake_ingest_field_telemetry
    hexcore._emit_goal_feedback = lambda **kwargs: None
    hexcore._apply_reward_to_reinforcement = lambda **kwargs: {
        "learning_rate": 0.2,
        "stability_factor": 1.1,
    }
    hexcore._apply_reinforcement_to_decision_influence = lambda **kwargs: {
        "ok": True,
        "dry_run": True,
    }

    hexcore.generate_thought = lambda decision: "reflection"
    hexcore.check_milestones = lambda: None
    hexcore.save_memory = lambda: None
    hexcore.sync_mind_state = lambda: None

    async def _fake_handle_action(input_str, decision):
        return None

    hexcore._handle_action = _fake_handle_action

    # -------------------------------------------------
    # Execute
    # -------------------------------------------------
    decision, entry = await HexCore.run_loop(hexcore, "run the field")

    # -------------------------------------------------
    # Assertions
    # -------------------------------------------------
    assert decision == "symatics-primary-decision"

    # Symatics must override QQC telemetry
    assert entry["coherence"] == pytest.approx(0.82)
    assert entry["delta_phi"] == pytest.approx(0.07)
    assert entry["psi"] == pytest.approx(0.18)
    assert entry["S_self"] == pytest.approx(0.74)

    # Raw Symatics should drive phi / kappa / T
    assert entry["phi"] == pytest.approx(1.23)
    assert entry["kappa"] == pytest.approx(0.44)
    assert entry["T"] == pytest.approx(0.66)

    # QQC still ran, but as secondary
    assert hexcore.qqc.calls, "QQC should still be called as secondary runtime"
    assert entry["qqc_summary"]["coherence"] == pytest.approx(0.12)
    assert entry["symatics_packet"] == symatics_packet

    # Reward path should see Symatics values, not QQC fallback values
    assert telemetry_seen["coherence"] == pytest.approx(0.82)
    assert telemetry_seen["dphi"] == pytest.approx(0.07)
    assert telemetry_seen["phi"] == pytest.approx(1.23)
    assert telemetry_seen["s_self"] == pytest.approx(0.74)

    assert entry["reward"] == pytest.approx(0.55)
    assert entry["goal_suggestions"] == ["increase_coherence"]

    assert entry["control"]["resonance_gain"] == pytest.approx(0.88)
    assert hexcore.last_field_control["resonance_gain"] == pytest.approx(0.88)

    assert hexcore.last_coherence == pytest.approx(0.82)
    assert hexcore.last_entropy == pytest.approx(0.18)
    assert hexcore.last_phi == pytest.approx(1.23)
    assert hexcore.delta_phi == pytest.approx(0.07)

    assert any(x["intent"] == "symatics_primary_runtime" for x in cfa_commits)