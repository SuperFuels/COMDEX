# ──────────────────────────────────────────────────────────────
#  Tessaris • Quantum Quad Core (QQC) Central Kernel (v2)
#  (HQCE + Multi-Core Integration Backbone)
#  Integrates Codex ↔ SQI ↔ Resonance ↔ Observer ↔ Knowledge ↔ Portal ↔ QFC
#  with ψ–κ–T holographic regulation and Lean theorem feedback.
# ──────────────────────────────────────────────────────────────

import asyncio
import time
import uuid
import logging
from typing import Dict, Any, Optional

# ─── Core Imports ─────────────────────────────────────────────
from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.codex.codex_core import CodexCore
from backend.modules.codex.codex_metrics import codex_metrics
from backend.modules.codex.codex_fabric import CodexFabric
from backend.modules.codex.codex_feedback_loop import CodexFeedbackLoop

from backend.modules.codex.symbolic_entropy import SQIEntropyField
from backend.modules.codex.symbolic_registry import SymbolicRegistry

from backend.modules.codex.holographic_cortex import HolographicCortex
from backend.modules.holograms.hst_generator import HSTGenerator
from backend.modules.holograms.morphic_feedback_controller import MorphicFeedbackController

from backend.modules.qfield.qfc_bridge import QFCBridge
from backend.modules.qfield.qfc_trigger_engine import QFCTriggerEngine
from backend.modules.qfield.qfc_ws_broadcast import QFCWebSocketBroadcast

from backend.modules.sqi.sqi_beam_kernel import SQIBeamKernel
from backend.modules.sqi.sqi_trace_logger import SQITraceLogger
from backend.modules.sqi.observer_engine import ObserverEngine

from backend.modules.teleport.portal_manager import PortalManager
from backend.modules.teleport.wormhole_manager import WormholeManager
from backend.modules.codex.container_exec import DimensionContainerExec

from backend.modules.sqi.kg_bridge import KnowledgeGraphBridge
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer

from backend.modules.lean.lean_adapter import LeanAdapter
from backend.modules.patterns.pattern_registry import PatternRegistry as PatternMatcher

from backend.QQC.qqc_commit_manager import QQCCommitManager
from backend.QQC.qqc_repair_manager import QQCRepairManager
from backend.modules.holograms.sle_lightwave_bridge import SLELightWaveBridge
from backend.modules.symbolic.hst.hst_websocket_streamer import broadcast_replay_paths

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
#  Quantum Quad Core v2 – Unified Orchestrator
# ──────────────────────────────────────────────────────────────
class QuantumQuadCore:
    """
    Unified orchestration layer across all QQC modules.
    Manages synchronization between symbolic, photonic, holographic, and quantum field layers.
    """

    def __init__(self, container_id: str = None, context: dict | None = None):
        # ───────────────────────────────
        #  Logging + Core Session Setup
        # ───────────────────────────────
        self.logger = logging.getLogger("QuantumQuadCore")
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.session_id = str(uuid.uuid4())
        self.container_id = container_id or self.session_id  # Backward compatibility alias
        self.boot_ts = time.time()
        self.cycle_counter = 0

        self.logger.info(f"[QQC v2] Initialized Tessaris Quantum Quad Core session → {self.session_id}")

        # ─── Core Subsystems ──────────────────────────────
        self.codex = CodexCore()
        self.codex_executor = CodexExecutor()
        self.codex_fabric = CodexFabric()
        self.feedback_loop = CodexFeedbackLoop()
        self.sqi = SQIEntropyField()
        self.symbolic_registry = SymbolicRegistry()
        self.holo_cortex = HolographicCortex()
        self.hst = HSTGenerator()
        self.feedback_controller = MorphicFeedbackController()

        # ─── Observer / Beam System ──────────────────────
        self.observer = ObserverEngine()
        self.beam_kernel = SQIBeamKernel()
        self.sqi_logger = SQITraceLogger()

        # ─── Container / Knowledge Integration ───────────
        self.container_runtime = DimensionContainerExec()
        self.kg_bridge = KnowledgeGraphBridge()
        self.kg_writer = get_kg_writer()

        # ─── Portal & Teleportation Systems ──────────────
        self.portal = PortalManager()
        self.wormhole = WormholeManager()

        # ─── Quantum Field Computation (QFC) ─────────────
        self.qfc_bridge = QFCBridge()
        self.qfc_trigger = QFCTriggerEngine()
        self.qfc_broadcast = QFCWebSocketBroadcast()

        # πₛ Phase Closure Bridge (QQC ↔ QFC ↔ GHX)
        from backend.symatics.qqc_qfc_adapter import qqc_qfc_adapter
        self.qqc_qfc_adapter = qqc_qfc_adapter
        self.qqc_qfc_adapter.start()

        # ─── Lean & Theorem Integration ──────────────────
        self.lean = LeanAdapter()
        self.patterns = PatternMatcher()

        # ─── Commit / Repair / Regulation Systems ────────
        self.commit_manager = QQCCommitManager()
        self.repair_manager = QQCRepairManager(self.hst)
        self.sle_bridge = SLELightWaveBridge(self.hst)

        # ─── State Cache ─────────────────────────────────
        self.last_summary: Optional[Dict[str, Any]] = None
        self.coherence_level = 0.0

        # ✅ Final confirmation
        self.logger.info(f"[QQC v2] ✅ Core subsystems initialized for session {self.session_id}")

    # ──────────────────────────────────────────────
    #  Boot Sequence
    # ──────────────────────────────────────────────
    async def boot(self, mode: str = "resonant"):
        logger.info(f"[QQC Boot] Starting in {mode} mode …")
        await self.holo_cortex.initialize()
        self.sqi_logger.start_session(self.session_id)
        self.feedback_loop.initialize()
        self.qfc_broadcast.start()
        logger.info("[QQC Boot] All subsystems initialized and synchronized.")

    # ──────────────────────────────────────────────
    #  Quantum Feedback / Runtime Cycle
    # ──────────────────────────────────────────────
    async def run_cycle(self, beam_data: Optional[Dict[str, Any]] = None):
        self.cycle_counter += 1
        try:
            # 1. Codex symbolic execution + SQI scoring
            codex_output = self.codex.execute(beam_data or {})
            sqi_score = self.sqi.evaluate_entropy(codex_output)

            # 2. Beam resonance propagation (includes physics telemetry)
            beam_state = self.beam_kernel.propagate(beam_data or {}, sqi_score)

            # 🧹 Strip physics telemetry before passing to Codex
            codex_payload = dict(beam_state)
            codex_payload.pop("physics", None)

            # 🚀 Execute symbolic photon capsule
            self.codex_executor.execute_photon_capsule(codex_payload)

            # 3. ψ–κ–T holographic regulation
            self.sle_bridge.inject_beam_feedback(beam_state)
            await self.feedback_controller.adjust_field(self.hst, sqi_score)

            # 4. Portal / Teleport synchronization
            self.portal.sync_state(self.container_runtime)
            self.wormhole.stabilize_links()

            # 5. Quantum Field broadcast
            self.qfc_trigger.update_field_state(self.hst.field_tensor)
            self.qfc_broadcast.send_state(self.session_id, self.hst.field_tensor)

            # 6. Two-Phase Commit: symbolic ↔ photonic ↔ holographic
            txn = self.commit_manager.commit_transaction(
                symbolic_state={"entropy": sqi_score, "src": "Codex"},
                photonic_state=beam_state,
                holographic_state=self.hst.field_tensor
            )

            # 7. Repair if instability detected
            repair_status = self.repair_manager.run_repair_cycle(txn)
            if repair_status.get("status") != "stable":
                logger.warning(f"[QQC Repair] Unstable coherence → {repair_status['status']}")

            # 8. Record and broadcast coherence summary
            self.last_summary = self.summarize_state()
            codex_metrics.record_execution_batch(
                adapter="qqc", op="run_cycle", payload=beam_data, result=self.last_summary
            )
            await self.broadcast_kernel_state()

            await asyncio.sleep(0.05)
            return self.last_summary

        except Exception as e:
            logger.error(f"[QQC v2] Runtime cycle error: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    # ──────────────────────────────────────────────
    #  State Summarization
    # ──────────────────────────────────────────────
    def summarize_state(self) -> Dict[str, Any]:
        coherence_vals = [n.get("coherence", 0.5) for n in self.hst.nodes.values()]
        avg_coherence = sum(coherence_vals) / len(coherence_vals) if coherence_vals else 0.0
        summary = {
            "session_id": self.session_id,
            "cycle": self.cycle_counter,
            "timestamp": time.time(),
            "coherence": avg_coherence,
            "entropy": self.sqi.last_entropy if hasattr(self.sqi, "last_entropy") else None,
            "portal_links": len(self.wormhole.active_links),
            "field_signature": self.hst.field_tensor,
        }
        logger.info(f"[QQC Summary] ⌀Coherence={avg_coherence:.3f} | ψκT={self.hst.field_tensor}")
        return summary

    # ──────────────────────────────────────────────
    #  Lean Proof Synchronization (Codex ↔ Lean)
    # ──────────────────────────────────────────────
    def sync_lean_proofs(self):
        """
        Perform a full Lean proof synchronization cycle:
        1. Export Codex/Symatics → Lean
        2. Verify Lean containers
        3. Generate visual proof graphs
        """
        try:
            # Reverse-generate Lean code from Codex container
            container = self.codex_fabric.get_current_container()
            self.lean.from_codex(container, "proofs/generated_axioms.lean")

            # Export a Symatics algebra expression as Lean axiom
            self.lean.from_symatics("∇⊗(λ⊗ψ) ⇒ λ∇⊗ψ", name="wave_resonance_axiom")

            # Verify the active container proofs
            from pathlib import Path

            container_path = Path(__file__).resolve().parent.parent / "modules/dimensions/containers/core.dc.json"
            self.lean.verify_container(str(container_path))

            # Generate proof visualization graph
            self.lean.visualize("backend/modules/dimensions/containers/core.dc.json", png_out="viz/core_graph.png")

            logger.info("[QQC → Lean] Proof sync and verification completed successfully.")
        except Exception as e:
            logger.error(f"[QQC → Lean] Proof sync failed: {e}", exc_info=True)

    # ──────────────────────────────────────────────
    #  Broadcast / Telemetry Layer
    # ──────────────────────────────────────────────
    async def broadcast_kernel_state(self):
        try:
            payload = {
                "type": "qqc_state",
                "session_id": self.session_id,
                "summary": self.last_summary or {},
            }
            broadcast_replay_paths(self.session_id, [])
            logger.debug("[QQC v2] Broadcast successful.")
        except Exception as e:
            logger.warning(f"[QQC v2] Broadcast failed: {e}")

    # ──────────────────────────────────────────────
    #  Teleportation & Portal Management
    # ──────────────────────────────────────────────
    async def teleport_state(self, src_container: str, dst_container: str):
        try:
            state = self.portal.extract_state(src_container)
            result = self.wormhole.transfer_state(state, dst_container)
            logger.info(f"[QQC Teleport] {src_container} → {dst_container} [{result}]")
            return result
        except Exception as e:
            logger.error(f"[QQC Teleport] Failed: {e}")
            return {"status": "error", "error": str(e)}

    # ──────────────────────────────────────────────
    #  Shutdown
    # ──────────────────────────────────────────────
    async def shutdown(self):
        logger.info("[QQC v2] Gracefully shutting down subsystems …")
        await self.qfc_broadcast.stop()
        await self.holo_cortex.teardown()
        self.sqi_logger.end_session(self.session_id)
        logger.info("[QQC v2] Shutdown complete.")

    def bind_hyperdrive_guard(self, enable: bool = False):
        """
        Controls QQC Hyperdrive safety mode.
        When enabled=True, safety circuits are bypassed for max performance.
        When disabled, all physical interfaces (GPIO, Wave Nozzles) stay in safe simulated mode.
        """
        self.hyperdrive_enabled = bool(enable)

        if enable:
            print("⚡ [QQC] Hyperdrive Mode ENABLED — full physical coupling active.")
            # Here you can enable direct GPIO / hardware interfaces
            # e.g., self.hardware_bridge.activate_full_output()
        else:
            print("🛑 [QQC] Safety Mode ENABLED — running in simulation (no GPIO).")
            # Ensure fallback to software-only loop
            # e.g., self.hardware_bridge.enter_safe_mode()

        # Optional: notify broadcast or logs
        try:
            from backend.modules.sqi.sqi_event_bus import log_info
            log_info(f"[QQC] Hyperdrive guard set → {enable}")
        except Exception:
            pass

    def run_codex_program(self, codex_str: str, context: dict | None = None) -> dict:
        """
        Runs a CodexLang program string through the full QQC pipeline.
        """
        from backend.modules.codex.codex_executor import CodexExecutor
        from backend.modules.codex.codex_metrics import score_glyph_tree
        from backend.modules.glyphvault.soul_law_validator import verify_transition
        import time, json

        context = context or {}
        context["container_id"] = self.container_id
        context["source"] = context.get("source", "QQC_Benchmark")

        print(f"[QQC] 🚀 Executing Codex program in container={self.container_id}")
        start_time = time.perf_counter()

        try:
            # 🧭 SoulLaw Veto Check (Ethical Preflight)
            if not verify_transition(context, codex_str):
                self.logger.warning(f"[❌ SoulLaw] Vetoed Codex program: {codex_str}")
                return {"error": "SoulLaw vetoed transition", "context": context}

            # ⚙️ Execute main Codex pipeline
            executor = CodexExecutor()
            result = executor.execute_codex_program(codex_str, context=context)
            duration = time.perf_counter() - start_time

            # Compute symbolic metrics
            symbolic_score = 0
            if isinstance(result, dict) and "instruction_tree" in result:
                symbolic_score = score_glyph_tree(result["instruction_tree"])
            elif isinstance(result, dict):
                symbolic_score = score_glyph_tree(result)

            # 🧠 SQI Rollback Monitoring
            if self.monitor_sqi_and_repair(symbolic_score, context):
                self.logger.info("[🌀] Rollback executed due to SQI degradation")

            # 🔍 Pattern Drift Detection + Fusion Repair
            try:
                from backend.modules.patterns.pattern_registry import PatternMatcher
                from backend.modules.qqc.qqc_repair_manager import RepairManager

                last_entropy = getattr(self, "_last_entropy", 0)
                new_entropy = len(json.dumps(result)) if result else 0
                self._last_entropy = new_entropy  # persist for next run comparison

                if PatternMatcher.detect_drift(last_entropy, new_entropy):
                    self.logger.warning(f"[⚠️ QQC] Pattern drift detected ({last_entropy} → {new_entropy})")
                    RepairManager.inject_fusion_glyph(context)
            except Exception as e:
                self.logger.debug(f"[QQC] Drift detection failed: {e}")

            # Structured telemetry
            telemetry = {
                "container_id": self.container_id,
                "duration_ms": round(duration * 1000, 2),
                "symbolic_score": symbolic_score,
                "entropy_estimate": len(json.dumps(result)) if result else 0,
                "hyperdrive": getattr(self, "hyperdrive_enabled", False),
            }

            # 🌐 Unified Knowledge Graph Export
            try:
                from backend.modules.sqi.kg_bridge import KnowledgeGraphBridge
                KnowledgeGraphBridge.export_all_traces(
                    symbolic_trace=context.get("symbolic_trace"),
                    photonic_trace=context.get("photonic_trace"),
                    holographic_trace=context.get("holographic_trace"),
                    container_id=self.container_id
                )
                self.logger.info("[📡 QQC] Exported unified KG traces successfully.")
            except Exception as e:
                self.logger.warning(f"[QQC] KG trace export failed: {e}")

            print(f"[QQC] ✅ Program executed in {telemetry['duration_ms']} ms")
            print(f"     Symbolic Score: {symbolic_score}")
            print(f"     Hyperdrive: {telemetry['hyperdrive']}")

            return {"result": result, "telemetry": telemetry}

        except Exception as e:
            self.logger.error(f"[QQC] Execution failed: {e}")
            return {"error": str(e), "context": context}

    # ───────────────────────────────────────────────
    # 🧩 SQI Threshold Monitoring / Rollback
    # ───────────────────────────────────────────────
    MIN_SQI_THRESHOLD = 2000  # adjust empirically

    def monitor_sqi_and_repair(self, sqi_score: float, context: dict):
        """Monitors SQI and triggers rollback if coherence lost."""
        if sqi_score < self.MIN_SQI_THRESHOLD:
            self.logger.warning(
                f"[⚠️ QQC] SQI below threshold ({sqi_score} < {self.MIN_SQI_THRESHOLD}) → initiating rollback"
            )
            from backend.modules.codex.codex_feedback_loop import CodexFeedbackLoop
            CodexFeedbackLoop.rollback_to_last_stable_state(context)
            return True
        return False

    # ────────────────────────────────────────────────
    # 💤 Graceful shutdown sequence
    # ────────────────────────────────────────────────

    import os, json, time
    from datetime import datetime

    def shutdown(self):
        """
        Gracefully shut down the QQC runtime:
        • Stop QFC adapter bridge
        • Validate πₛ closure
        • Dump telemetry + closure report to sle_validation.json
        """
        # ────────────────────────────────────────────────
        # 1️⃣ Stop QFC Adapter Bridge
        # ────────────────────────────────────────────────
        if hasattr(self, "qqc_qfc_adapter") and self.qqc_qfc_adapter.active:
            self.qqc_qfc_adapter.stop()

        # ────────────────────────────────────────────────
        # 2️⃣ Validate πₛ Phase Closure
        # ────────────────────────────────────────────────
        try:
            from backend.symatics.pi_phase_validator import PhaseClosureValidator
            validator = PhaseClosureValidator()
            metrics = (
                self.qqc_qfc_adapter.latest_metrics(20)
                if hasattr(self, "qqc_qfc_adapter")
                else []
            )
            closure_ok = validator.validate(metrics)
            closure_report = validator.report()
        except Exception as e:
            closure_ok = False
            closure_report = {"error": str(e)}

        # ────────────────────────────────────────────────
        # 3️⃣ Export Telemetry → sle_validation.json
        # ────────────────────────────────────────────────
        try:
            export_dir = "./exports/telemetry"
            os.makedirs(export_dir, exist_ok=True)

            payload = {
                "session_id": getattr(self, "session_id", None),
                "timestamp": datetime.utcnow().isoformat(),
                "closure_ok": closure_ok,
                "closure_report": closure_report,
                "metrics": metrics,
            }

            export_path = os.path.join(
                export_dir, f"sle_validation_{int(time.time())}.json"
            )
            with open(export_path, "w") as f:
                json.dump(payload, f, indent=2)

            self.logger.info(f"[QQC] 🧭 Telemetry exported → {export_path}")
        except Exception as e:
            self.logger.warning(f"[QQC] Telemetry export failed: {e}")

        # ────────────────────────────────────────────────
        # 4️⃣ Final Log
        # ────────────────────────────────────────────────
        self.logger.info("[QQC] Graceful shutdown completed.")
        self.logger.info(f"[QQC] πₛ closure = {'✅ stable' if closure_ok else '⚠️ incomplete'}")

# ──────────────────────────────────────────────────────────────
#  CLI Harness / Standalone Mode
# ──────────────────────────────────────────────────────────────
import asyncio
import time

async def main():
    qqc = QQCCentralKernel()
    await qqc.boot(mode="resonant")

    for i in range(5):
        beam_data = {
            "beam_id": f"ψ_{i}",
            "coherence": 0.7 + 0.05 * i,
            "phase_shift": 0.01 * i,
            "entropy_drift": 0.02 * (i - 2),
            "gain": 1.0 + 0.1 * i,
            "timestamp": time.time(),
        }
        await qqc.run_cycle(beam_data)

    # 🧩 Once runtime has stabilized, sync proofs with Lean
    qqc.sync_lean_proofs()

    await qqc.broadcast_kernel_state()
    await qqc.teleport_state("core_alpha", "core_beta")

    print("\n🧭 Final QQC Summary:")
    print(qqc.last_summary)
    await qqc.shutdown()


if __name__ == "__main__":
    asyncio.run(main())