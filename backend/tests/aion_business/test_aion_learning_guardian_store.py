from __future__ import annotations

import base64
import asyncio
from decimal import Decimal
import hashlib

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_learning.runtime import AionLearningRuntime
from backend.modules.aion_learning.contracts_decision_influence import DecisionInfluenceUpdate
from backend.modules.aion_learning.decision_influence_runtime import DecisionInfluenceRuntime
from backend.modules.aion_learning.teaching_memory_store import TeachingMemoryStore
from backend.modules.aion_learning.vault_store import AionLearningVaultStore
from backend.modules.aion_inference.glyph_context import GlyphContextDictionary
from backend.modules.aion_inference.adaptive_runtime import AdaptiveInferenceRuntime
from backend.modules.aion_inference.learned_atomsheets import (
    LearnedAtomSheetStore,
    VerifiedModelOutcome,
)
from backend.modules.aion_learning.gradient_correction_layer import GradientCorrectionLayer
from backend.modules.aion_learning.resonance_state_manager import ResonanceStateManager
from backend.modules.aion_learning.llm_weighting_runtime import LLMWeightingRuntime
from backend.modules.aion_prediction.predictive_bias_layer import PredictiveBias
from backend.modules.aion_prediction.temporal_coherence_memory import TemporalCoherenceMemory
from backend.modules.aion_resonance.resonance_state import (
    load_phi_state,
    reset_phi_state,
    save_phi_state,
)
from backend.modules.aion_resonance.conversation_memory import ConversationMemory
from backend.modules.aion_resonance.aion_symbolic_mapper import (
    get_recent_symbolic_reflections,
    process_event,
)
from backend.modules.aion_resonance.symatic_bridge import generate_symatic_equation
from backend.modules.aion_resonance.symatic_event_store import SymaticEventStore
from backend.modules.aion_resonance.resonance_lexicon_store import ResonanceLexiconStore
from backend.modules.aion_resonance.reinforcement_mixin import ResonantReinforcementMixin
from backend.modules.aion_resonance.phi_drift_log import get_drift_history, record_phi_drift
from backend.modules.aion_resonance.phi_graph import PhiGraph
from backend.modules.aion_resonance import phi_learning
from backend.modules.aion_resonance.phi_reinforce import (
    get_reinforce_state,
    reinforce_from_memory,
    reset_reinforce_state,
    update_beliefs,
)


def _domain_store(tmp_path):
    layout = provision_business_vault(
        tmp_path / "customer-vault",
        business_name="Private Workshop",
        business_stable_id="private-workshop",
        application_root=tmp_path / "application",
        update_root=tmp_path / "updates",
    )
    return layout, VaultDomainStore(
        VaultGuardian(
            layout,
            business_stable_id="private-workshop",
            encryption_key=b"l" * 32,
        ),
        actor_id="aion-learning-test",
    )


def test_customer_teaching_and_skill_learning_are_guardian_records(tmp_path):
    layout, domains = _domain_store(tmp_path)
    learning_store = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    teaching = TeachingMemoryStore(vault_store=learning_store)
    teaching.upsert_concept(
        concept_label="Private pricing rule",
        corrected_response="Never expose the customer's cost price",
        target_confidence=0.95,
        notes="Founder correction",
    )

    runtime = AionLearningRuntime(
        vault_store=learning_store,
        weakness_fail_threshold=2,
        weakness_min_fail_rate=0.5,
    )
    for run_id in ("private-run-1", "private-run-2"):
        runtime.record_skill_run(
            skill_id="private.customer.quote",
            skill_run_id=run_id,
            ok=False,
            error_code="customer_private_failure",
            metadata={"customer_name": "Private Client"},
        )

    assert len(runtime.list_events(limit=10)) == 2
    assert runtime.get_weakness_signals()[0]["skill_id"] == "private.customer.quote"

    restarted_learning = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    restarted_teaching = TeachingMemoryStore(vault_store=restarted_learning)
    assert (
        restarted_teaching.get_concept("Private pricing rule")["corrected_response"]
        == "Never expose the customer's cost price"
    )
    restarted_runtime = AionLearningRuntime(vault_store=restarted_learning)
    assert [row["skill_run_id"] for row in restarted_runtime.list_events(limit=10)] == [
        "private-run-1",
        "private-run-2",
    ]

    assert not (tmp_path / ".runtime").exists()
    assert not (tmp_path / "data").exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"Private Client" not in database_bytes
    assert b"Never expose the customer's cost price" not in database_bytes
    assert domains.guardian.verify_audit_chain()["healthy"] is True


def test_inference_glyph_dictionary_restarts_from_encrypted_learning_state(tmp_path):
    layout, domains = _domain_store(tmp_path)
    learning_store = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    raw_path = tmp_path / "application" / "glyph-context.sqlite3"
    passages = (
        "Policy: never expose Private Workshop cost prices.",
        "Private Client requested a protected quotation.",
    )

    first = GlyphContextDictionary(
        raw_path,
        dictionary_id="private-workshop-context.v1",
        vault_store=learning_store,
    )
    packet = first.encode(passages)
    restarted = GlyphContextDictionary(
        tmp_path / "different-application" / "ignored.sqlite3",
        dictionary_id="private-workshop-context.v1",
        vault_store=learning_store,
    )

    assert restarted.known_slots() == {1, 2}
    assert restarted.decode(packet) == passages
    assert not raw_path.exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"Private Workshop cost prices" not in database_bytes
    assert b"Private Client" not in database_bytes


def test_adaptive_inference_replay_and_trace_restart_from_guardian(tmp_path):
    layout, domains = _domain_store(tmp_path)
    learning_store = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    replay_path = tmp_path / "application" / "replay.sqlite3"
    trace_path = tmp_path / "application" / "trace.jsonl"

    first_runtime = AdaptiveInferenceRuntime(
        replay_path=replay_path,
        trace_path=trace_path,
        vault_store=learning_store,
    )
    first = first_runtime.route("What is 15% of 240?")
    restarted = AdaptiveInferenceRuntime(
        replay_path=tmp_path / "changed-application" / "ignored.sqlite3",
        trace_path=tmp_path / "changed-application" / "ignored.jsonl",
        vault_store=learning_store,
    )
    second = restarted.route("What is 15% of 240?")

    assert first.route == "verified_atomsheet"
    assert second.route == "verified_replay"
    assert len(learning_store.list_events(kind="aion_inference_trace")) == 2
    assert not replay_path.exists()
    assert not trace_path.exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"verified_atomsheet" not in database_bytes
    assert b"What is 15%" not in database_bytes


def test_learned_atomsheet_quarantine_and_promotion_restart_from_guardian(tmp_path):
    layout, domains = _domain_store(tmp_path)
    learning_store = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    raw_database = tmp_path / "application" / "learning.sqlite3"
    raw_promoted = tmp_path / "application" / "promoted"
    store = LearnedAtomSheetStore(
        raw_database,
        raw_promoted,
        vault_store=learning_store,
    )
    for index, (cost, percent) in enumerate(
        (("100", "10"), ("80", "25"), ("50", "20"), ("240", "15"), ("12", "50"), ("400", "7"))
    ):
        result = str(Decimal(cost) * (Decimal("1") + Decimal(percent) / Decimal("100")))
        store.observe(
            VerifiedModelOutcome(
                intent="CALCULATE_MARKED_UP_PRICE",
                inputs={"cost": cost, "markup_percent": percent},
                result=result,
                verifier_id=f"private-verifier-{index % 2}",
                model_id="private-local-model",
                response_sha256=hashlib.sha256(
                    f"private-response-{index}".encode()
                ).hexdigest(),
                created_at=f"2026-10-18T01:00:{index:02d}+00:00",
            )
        )

    restarted = LearnedAtomSheetStore(
        tmp_path / "changed-application" / "ignored.sqlite3",
        tmp_path / "changed-application" / "ignored-promoted",
        vault_store=learning_store,
    )
    execution = restarted.execute(
        "CALCULATE_MARKED_UP_PRICE",
        {"cost": "150", "markup_percent": "60"},
    )

    assert restarted.status()["verified_outcomes"] == 6
    assert execution.structured_result == {"value": "240"}
    assert execution.model_call_required is False
    assert not raw_database.exists()
    assert not raw_promoted.exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"private-local-model" not in database_bytes
    assert b"CALCULATE_MARKED_UP_PRICE" not in database_bytes


def test_default_learning_stores_obey_guardian_environment(tmp_path, monkeypatch):
    vault_path = tmp_path / "external-business-vault"
    env = {
        "TESSARIS_BUSINESS_CONTAINER_BACKEND": "guardian",
        "TESSARIS_BUSINESS_VAULT_PATH": str(vault_path),
        "TESSARIS_BUSINESS_NAME": "Environment Workshop",
        "TESSARIS_BUSINESS_STABLE_ID": "environment-workshop",
        "TESSARIS_BUSINESS_VAULT_KEY_B64": base64.urlsafe_b64encode(
            b"e" * 32
        ).decode().rstrip("="),
        "TESSARIS_APPLICATION_ROOT": str(tmp_path / "application"),
        "TESSARIS_UPDATE_ROOT": str(tmp_path / "updates"),
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(tmp_path)

    TeachingMemoryStore().upsert_concept(
        concept_label="Environment-only teaching",
        corrected_response="Store this outside the application",
        target_confidence=0.9,
    )
    AionLearningRuntime().record_skill_run(
        skill_id="environment.private.skill",
        skill_run_id="environment-run-1",
        ok=True,
        metadata={"private": "environment-customer-data"},
    )

    assert TeachingMemoryStore().get_concept("Environment-only teaching") is not None
    assert AionLearningRuntime().list_events(limit=10)[0]["skill_run_id"] == "environment-run-1"
    assert not (tmp_path / "data" / "logs" / "phase0_learning_memory.json").exists()
    assert not (tmp_path / ".runtime" / "COMDEX_MOVE" / "data" / "learning").exists()


def test_explicit_paths_remain_available_for_test_and_copy_migration(tmp_path):
    teaching_path = tmp_path / "legacy" / "teaching.json"
    teaching = TeachingMemoryStore(teaching_path)
    teaching.upsert_concept(
        concept_label="Legacy teaching",
        corrected_response="Retain until copy verification completes",
        target_confidence=0.8,
    )
    runtime_root = tmp_path / "legacy-runtime"
    runtime = AionLearningRuntime(data_root=str(runtime_root))
    runtime.record_skill_run(
        skill_id="legacy.skill",
        skill_run_id="legacy-run",
        ok=True,
    )

    assert teaching_path.exists()
    assert (runtime_root / "learning" / "aion_learning_events.jsonl").exists()


def test_decision_influence_state_and_audit_survive_guardian_restart(tmp_path):
    layout, domains = _domain_store(tmp_path)
    learning_store = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    runtime = DecisionInfluenceRuntime(vault_store=learning_store)
    result = runtime.apply_update(
        DecisionInfluenceUpdate(
            session_id="private-session",
            turn_id="private-turn",
            source="founder-correction",
            reason="Private customer decision correction",
            confidence=0.9,
            updates={"llm_trust_weights": {"private-route": 1.25}},
            metadata={"customer_name": "Private Decision Customer"},
        ),
        dry_run=False,
    )
    assert result["ok"] is True
    assert runtime.weights_version == 2

    restarted = DecisionInfluenceRuntime(vault_store=learning_store)
    assert restarted.weights_version == 2
    assert restarted.state["llm_trust_weights"]["private-route"] == 1.25
    assert restarted._replay_state_to_version(2)["llm_trust_weights"]["private-route"] == 1.25
    assert len(
        learning_store.list_events(kind="decision_influence_audit")
    ) == 1

    assert not (tmp_path / ".runtime").exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"Private Decision Customer" not in database_bytes
    assert b"Private customer decision correction" not in database_bytes


def test_resonance_state_and_private_correction_vectors_use_guardian(tmp_path):
    layout, domains = _domain_store(tmp_path)
    learning_store = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    manager = ResonanceStateManager(vault_store=learning_store)
    manager.update(0.42, 0.91)

    layer = GradientCorrectionLayer(vault_store=learning_store)
    layer.log_delta(
        [1.0, 2.0, 3.0],
        [1.1, 2.2, 3.3],
        0.374,
        0.64,
    )

    restarted = ResonanceStateManager(vault_store=learning_store)
    assert restarted.state["avg_strength"] == 0.42
    assert restarted.state["decay_rate"] == 0.91
    correction_events = learning_store.list_events(kind="gradient_correction")
    assert correction_events[0]["actual_vec"] == [1.1, 2.2, 3.3]
    assert not (tmp_path / "data").exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"predicted_vec" not in database_bytes
    assert b"actual_vec" not in database_bytes


def test_llm_accuracy_evidence_uses_guardian_and_remains_queryable(tmp_path):
    layout, domains = _domain_store(tmp_path)
    learning_store = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    runtime = LLMWeightingRuntime(vault_store=learning_store)
    logged = runtime.log_llm_accuracy(
        llm_id="private-local-model",
        pair="PRIVATE/PAIR",
        session="private-customer-session",
        predicted_bias="BULLISH",
        actual_outcome_bias="BULLISH",
        metadata={"customer": "Private Accuracy Customer"},
        ts=100.0,
    )
    assert logged["path"].startswith("vault://learning.audit/")

    restarted = LLMWeightingRuntime(vault_store=learning_store)
    summary = restarted.summarize_llm_accuracy()
    assert summary["matched_rows"] == 1
    assert summary["per_llm"]["private-local-model"]["n"] == 1
    assert not (tmp_path / ".runtime").exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"Private Accuracy Customer" not in database_bytes
    assert b"private-customer-session" not in database_bytes


def test_prediction_memory_state_and_evidence_use_guardian(tmp_path):
    layout, domains = _domain_store(tmp_path)
    learning_store = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    memory = TemporalCoherenceMemory(vault_store=learning_store)
    for symbol in ("PRIVATE-A", "PRIVATE-B", "PRIVATE-C"):
        memory.update_sequence(symbol)
    memory.update_markov("PRIVATE-C", "PRIVATE-D")

    bias = PredictiveBias(vault_store=learning_store)
    bias.update("PRIVATE-C", "PRIVATE-D", reward=0.8)
    bias.last_prediction = "PRIVATE-D"
    assert bias.evaluate("PRIVATE-D") == 1.0
    bias.save_state()
    bias.observe("PRIVATE-C")
    bias.observe("PRIVATE-D")
    bias.save_temporal_model()

    restarted_memory = TemporalCoherenceMemory(vault_store=learning_store)
    assert restarted_memory.markov_graph["PRIVATE-C"]["PRIVATE-D"] == 1.0
    restarted_bias = PredictiveBias(vault_store=learning_store)
    restarted_bias.load_state()
    assert restarted_bias.transitions[("PRIVATE-C", "PRIVATE-D")] > 0
    assert learning_store.get_state("predictive_temporal_model", None) is not None
    assert len(learning_store.list_events(kind="temporal_sequence")) == 1
    assert len(learning_store.list_events(kind="predictive_transition")) == 1
    assert len(learning_store.list_events(kind="predictive_evaluation")) == 1

    assert not (tmp_path / "data").exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"PRIVATE-A" not in database_bytes
    assert b"PRIVATE-D" not in database_bytes


def test_prediction_explicit_paths_preserve_legacy_copy_source(tmp_path, monkeypatch):
    # A retained source/copy-migration tool may run on a Guardian-configured
    # node. Explicit paths must stay explicit rather than silently selecting
    # the live business authority.
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "guardian")
    buffer_path = tmp_path / "legacy" / "temporal_buffer.jsonl"
    model_path = tmp_path / "legacy" / "temporal_model.json"
    state_path = tmp_path / "legacy" / "predictive_bias_state.json"
    log_path = tmp_path / "legacy" / "predictive_transitions.jsonl"

    memory = TemporalCoherenceMemory(
        buffer_path=buffer_path,
        model_path=model_path,
    )
    for symbol in ("A", "B", "C"):
        memory.update_sequence(symbol)
    memory.update_markov("C", "D")

    bias = PredictiveBias(
        model_path=model_path,
        state_path=state_path,
        log_path=log_path,
    )
    bias.update("C", "D", reward=1.0)
    bias.save_state()
    bias.save_temporal_model()

    assert buffer_path.exists()
    assert model_path.exists()
    assert state_path.exists()
    assert log_path.exists()


def test_aion_phi_state_uses_guardian_and_legacy_paths_are_explicit(tmp_path):
    layout, domains = _domain_store(tmp_path)
    learning_store = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    saved = save_phi_state(
        {"Φ_coherence": 0.88, "Φ_entropy": 0.2, "private": "customer-signal"},
        last_command="PRIVATE-CUSTOMER-COMMAND",
        vault_store=learning_store,
    )
    assert saved["Φ_coherence"] == 0.88
    assert load_phi_state(vault_store=learning_store)["last_command"] == (
        "PRIVATE-CUSTOMER-COMMAND"
    )
    reset_phi_state(vault_store=learning_store)
    assert load_phi_state(vault_store=learning_store)["last_command"] == "reset"
    assert not (tmp_path / "backend" / "state" / "resonance_state.json").exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"customer-signal" not in database_bytes
    assert b"PRIVATE-CUSTOMER-COMMAND" not in database_bytes

    legacy_path = tmp_path / "legacy" / "resonance_state.json"
    save_phi_state(
        {"Φ_coherence": 0.7, "Φ_entropy": 0.3},
        last_command="legacy",
        state_path=legacy_path,
    )
    assert load_phi_state(state_path=legacy_path)["last_command"] == "legacy"


def test_conversation_memory_uses_guardian_and_has_explicit_legacy_mode(tmp_path):
    layout, domains = _domain_store(tmp_path)
    learning_store = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    memory = ConversationMemory(vault_store=learning_store, max_memory=2)
    memory.record(
        "PRIVATE-COMMAND-1",
        {"Φ_coherence": 0.7, "Φ_entropy": 0.3},
        {"private": "first customer reasoning"},
    )
    memory.record(
        "PRIVATE-COMMAND-2",
        {"Φ_coherence": 0.9, "Φ_entropy": 0.1},
        {"private": "second customer reasoning"},
    )
    restarted = ConversationMemory(vault_store=learning_store, max_memory=2)
    assert [row["command"] for row in restarted.load()] == [
        "PRIVATE-COMMAND-1", "PRIVATE-COMMAND-2",
    ]
    assert restarted.get_recent()["summary"]["avg_coherence"] == 0.8
    assert not (tmp_path / "data" / "conversation_memory.json").exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"PRIVATE-COMMAND" not in database_bytes
    assert b"customer reasoning" not in database_bytes

    legacy_path = tmp_path / "legacy" / "conversation_memory.json"
    legacy = ConversationMemory(memory_path=legacy_path)
    legacy.record(
        "legacy-command",
        {"Φ_coherence": 0.5, "Φ_entropy": 0.5},
        {},
    )
    assert ConversationMemory(memory_path=legacy_path).load()[0]["command"] == (
        "legacy-command"
    )


def test_symbolic_reflections_use_immutable_guardian_events(tmp_path):
    layout, domains = _domain_store(tmp_path)
    learning_store = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )

    class ForbiddenLegacyMemory:
        def store(self, _payload):
            raise AssertionError("Guardian symbolic memory reached legacy HexCore")

    asyncio.run(
        process_event(
            "reflect",
            {"Φ_coherence": 0.93, "private": "customer phi"},
            {"private": "customer belief"},
            vault_store=learning_store,
            legacy_memory_engine=ForbiddenLegacyMemory(),
        )
    )
    rows = get_recent_symbolic_reflections(
        vault_store=AionLearningVaultStore(
            domain_store=domains,
            workspace_id="private-workshop",
        )
    )
    assert len(rows) == 1
    assert rows[0]["event_type"] == "symbolic_reflection"
    assert rows[0]["belief"]["private"] == "customer belief"
    assert not (tmp_path / "data" / "symbolic_memory.json").exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"customer belief" not in database_bytes
    assert b"customer phi" not in database_bytes

    class LegacyMemory:
        def __init__(self):
            self.rows = []

        def store(self, payload):
            self.rows.append(payload)

    legacy_engine = LegacyMemory()
    legacy_path = tmp_path / "legacy" / "symbolic_memory.json"
    asyncio.run(
        process_event(
            "collect",
            {"Φ_coherence": 0.5},
            {},
            memory_path=legacy_path,
            legacy_memory_engine=legacy_engine,
        )
    )
    assert get_recent_symbolic_reflections(memory_path=legacy_path)[0]["event"] == (
        "collect"
    )
    assert legacy_engine.rows[0]["label"] == "symbolic_collect"


def test_symatic_equations_and_reflections_use_guardian(tmp_path):
    layout, domains = _domain_store(tmp_path)
    learning_store = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    events = SymaticEventStore(vault_store=learning_store)
    conversation = ConversationMemory(vault_store=learning_store)
    entry = generate_symatic_equation(
        {"Φ_coherence": 0.5, "Φ_entropy": 0.4, "Φ_flux": 0.1},
        {"Φ_coherence": 0.8, "Φ_entropy": 0.2, "Φ_flux": 0.3},
        "PRIVATE-CUSTOMER-EQUATION-REFLECTION",
        event_store=events,
        conversation_memory=conversation,
    )
    assert entry["operator"] == "⟲"
    restarted = SymaticEventStore(
        vault_store=AionLearningVaultStore(
            domain_store=domains,
            workspace_id="private-workshop",
        )
    )
    rows = restarted.list()
    assert rows[0]["event_type"] == "symatic_equation"
    assert rows[0]["reflection"] == "PRIVATE-CUSTOMER-EQUATION-REFLECTION"
    assert ConversationMemory(vault_store=learning_store).load()[0]["command"].startswith(
        "SYMATICS:"
    )
    assert not (tmp_path / "data" / "symatic_log.json").exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"PRIVATE-CUSTOMER-EQUATION-REFLECTION" not in database_bytes

    legacy_path = tmp_path / "legacy" / "symatic_log.json"
    legacy = SymaticEventStore(path=legacy_path)
    legacy.record("mu", "legacy equation")
    assert SymaticEventStore(path=legacy_path).list()[0]["equation"] == (
        "legacy equation"
    )


def test_resonance_lexicon_separates_product_base_from_customer_overrides(tmp_path):
    layout, domains = _domain_store(tmp_path)
    base_path = tmp_path / "application" / "boot_config.json"
    base_path.parent.mkdir(parents=True, exist_ok=True)
    base_path.write_text(
        '{"affirmative":{"\u03a6_coherence":0.99,"\u03a6_entropy":0.1}}',
        encoding="utf-8",
    )
    original = base_path.read_bytes()
    learning_store = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    lexicon = ResonanceLexiconStore(
        vault_store=learning_store,
        base_path=base_path,
    )
    lexicon.put(
        "private-customer-term",
        {"\u03a6_coherence": 0.73, "\u03a6_entropy": 0.27},
    )
    lexicon.put(
        "affirmative",
        {"\u03a6_coherence": 0.88, "\u03a6_entropy": 0.12},
    )

    restarted = ResonanceLexiconStore(
        vault_store=AionLearningVaultStore(
            domain_store=domains,
            workspace_id="private-workshop",
        ),
        base_path=base_path,
    )
    assert restarted.load()["private-customer-term"]["\u03a6_coherence"] == 0.73
    assert restarted.load()["affirmative"]["\u03a6_coherence"] == 0.88
    assert base_path.read_bytes() == original
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"private-customer-term" not in database_bytes

    legacy_path = tmp_path / "legacy" / "learned_lexicon.json"
    legacy = ResonanceLexiconStore(
        base_path=base_path,
        legacy_path=legacy_path,
    )
    legacy.put("legacy-term", {"\u03a6_coherence": 0.5})
    assert ResonanceLexiconStore(
        base_path=base_path,
        legacy_path=legacy_path,
    ).load()["legacy-term"]["\u03a6_coherence"] == 0.5


def test_phi_reinforcement_state_and_memory_use_guardian(tmp_path):
    layout, domains = _domain_store(tmp_path)
    learning_store = AionLearningVaultStore(
        domain_store=domains,
        workspace_id="private-workshop",
    )
    memory = ConversationMemory(vault_store=learning_store)
    for position, coherence in enumerate((0.82, 0.9, 0.94), start=1):
        memory.record(
            f"PRIVATE-REINFORCEMENT-{position}",
            {"\u03a6_coherence": coherence, "\u03a6_entropy": 0.2},
            {"private": "customer reinforcement evidence"},
        )
    state = reinforce_from_memory(
        vault_store=learning_store,
        conversation_memory=memory,
    )
    assert state["\u03a6_coherence"] > 0.65
    updated = update_beliefs(
        {"trust": 0.1},
        vault_store=learning_store,
    )
    assert updated["beliefs"]["trust"] > state["beliefs"]["trust"]
    restarted = get_reinforce_state(
        vault_store=AionLearningVaultStore(
            domain_store=domains,
            workspace_id="private-workshop",
        )
    )
    assert restarted["beliefs"]["trust"] == updated["beliefs"]["trust"]
    assert not (tmp_path / "data" / "phi_reinforce_state.json").exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"PRIVATE-REINFORCEMENT" not in database_bytes
    assert b"customer reinforcement evidence" not in database_bytes

    legacy_path = tmp_path / "legacy" / "phi_reinforce_state.json"
    reset_reinforce_state(state_path=legacy_path)
    assert get_reinforce_state(state_path=legacy_path)["\u03a6_coherence"] == 0.65


def test_phi_trace_drift_and_relationship_graph_use_guardian(tmp_path, monkeypatch):
    layout, domains = _domain_store(tmp_path)
    learning_store = AionLearningVaultStore(
        domain_store=domains, workspace_id="private-workshop"
    )
    monkeypatch.setattr(phi_learning, "_reinforce_personality", lambda _phi: None)
    phi_learning.update_phi_state(
        {"\u03a6_coherence": 0.9, "\u03a6_entropy": 0.2, "\u03a6_flux": 0.1, "\u03a6_load": 0.0},
        "PRIVATE-PHI-LEARNING",
        vault_store=learning_store,
    )
    record_phi_drift(
        "private-term", {"\u03a6_coherence": 0.9, "\u03a6_entropy": 0.2},
        vault_store=learning_store,
    )
    graph = PhiGraph(vault_store=learning_store)
    graph.add_node("private-term", {"\u03a6_coherence": 0.9, "tone": "harmonic"})
    graph.add_node("private-peer", {"\u03a6_coherence": 0.8, "tone": "harmonic"})
    graph.add_entanglement("private-term", "private-peer", "similar", 0.8)

    events = learning_store.list_events()
    assert {row["event_type"] for row in events} >= {"phi_learning_trace", "phi_drift"}
    assert get_drift_history(vault_store=learning_store)[0]["keyword"] == "private-term"
    restarted = PhiGraph(
        vault_store=AionLearningVaultStore(
            domain_store=domains, workspace_id="private-workshop"
        )
    )
    assert "private-term↔private-peer" in restarted.snapshot()["edges"]
    for name in ("phi_trace.json", "phi_drift_log.json", "phi_graph.json"):
        assert not (tmp_path / "data" / name).exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"private-term" not in database_bytes
    assert b"PRIVATE-PHI-LEARNING" not in database_bytes


def test_resonance_reinforcement_history_uses_guardian_and_legacy_copy_source(tmp_path):
    layout, domains = _domain_store(tmp_path)
    learning_store = AionLearningVaultStore(
        domain_store=domains, workspace_id="private-workshop"
    )
    reinforcement = ResonantReinforcementMixin(
        "private-engine", vault_store=learning_store
    )
    reinforcement.update_resonance_feedback(
        0.7, reason="PRIVATE-CUSTOMER-OUTCOME"
    )

    restarted = ResonantReinforcementMixin(
        "private-engine",
        vault_store=AionLearningVaultStore(
            domain_store=domains, workspace_id="private-workshop"
        ),
    )
    rows = restarted.get_reinforcement_history()
    assert len(rows) == 1
    assert rows[0]["event_type"] == "resonance_reinforcement_snapshot"
    assert rows[0]["engine_name"] == "private-engine"
    assert rows[0]["note"] == "PRIVATE-CUSTOMER-OUTCOME"
    assert not (tmp_path / "data" / "telemetry" / "private-engine_resonance_history.json").exists()
    database_bytes = (layout.records / "guardian.sqlite3").read_bytes()
    assert b"PRIVATE-CUSTOMER-OUTCOME" not in database_bytes

    legacy_path = tmp_path / "legacy" / "private-engine_resonance_history.json"
    legacy = ResonantReinforcementMixin(
        "private-engine", history_path=legacy_path
    )
    legacy.update_resonance_feedback(0.4, reason="legacy outcome")
    assert legacy_path.exists()
    assert ResonantReinforcementMixin(
        "private-engine", history_path=legacy_path
    ).get_reinforcement_history()[0]["note"] == "legacy outcome"
