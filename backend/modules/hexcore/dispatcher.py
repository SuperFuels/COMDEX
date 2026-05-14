# backend/modules/hexcore/dispatcher.py
# ──────────────────────────────────────────────────────────────
#  Tessaris * Cognitive Dispatcher (v2)
#  Routes AION intents to active subsystems:
#   QQC * Lean * KnowledgeGraph * MorphicLedger * Reflection
#  Enables command-level orchestration of all Tessaris engines
# ──────────────────────────────────────────────────────────────

import asyncio
import logging
from typing import Any, Dict

# Core Engine Imports
from backend.QQC.qqc_central_kernel import QuantumQuadCore
from backend.modules.lean.lean_adapter import LeanAdapter
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.holograms.morphic_ledger import MorphicLedger

# Optional extensions
try:
    from backend.modules.hqce.metrics import compute_phi_metrics
except ImportError:
    compute_phi_metrics = None

logger = logging.getLogger("CognitiveDispatcher")


# ──────────────────────────────────────────────────────────────
#  Dispatcher Class
# ──────────────────────────────────────────────────────────────
class CognitiveDispatcher:
    """
    Central orchestration bridge between AION (HexCore) and Tessaris subsystems.
    Parses intent -> routes execution -> returns structured telemetry.
    """

    def __init__(self):
        self.qqc = QuantumQuadCore()
        self.lean = LeanAdapter()
        self.kg = get_kg_writer()
        self.ledger = MorphicLedger()

    # ──────────────────────────────────────────────
    #  Main Execution Router
    # ──────────────────────────────────────────────
    async def execute(self, intent: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Routes a natural-language or symbolic intent to the correct Tessaris subsystem.
        Returns a structured result object.
        """
        intent = intent.lower().strip()
        logger.info(f"[Dispatcher] Received intent -> '{intent}'")

        try:
            # 1️⃣ Quantum Resonance / QQC task
            if any(k in intent for k in ["qqc", "resonance", "solve", "math", "tensor", "qfield"]):
                logger.info("[Dispatcher] -> Routing to QQC")
                result = await self.qqc.run_cycle(payload)
                self._log_to_ledger("QQC", payload, result)
                return {"source": "QQC", "status": "ok", "result": result}

            # 2️⃣ Lean Proof / Formal Verification
            elif any(k in intent for k in ["lean", "proof", "verify", "axiom"]):
                logger.info("[Dispatcher] -> Routing to Lean")
                path = payload.get("path", "backend/modules/dimensions/containers/core.dc.json")
                self.lean.verify_container(path)
                self._log_to_ledger("Lean", payload, {"verified_path": path})
                return {"source": "Lean", "status": "verified", "path": path}

            # 3️⃣ Knowledge Graph Storage
            elif any(k in intent for k in ["knowledge", "graph", "store", "record", "export"]):
                logger.info("[Dispatcher] -> Routing to KnowledgeGraph")
                self.kg.write_entry(payload)
                self._log_to_ledger("KnowledgeGraph", payload, {"stored": True})
                return {"source": "KnowledgeGraph", "status": "stored"}

            # 4️⃣ Reflective / Awareness task (Φ computation)
            elif any(k in intent for k in ["reflect", "awareness", "observe", "resonate"]):
                logger.info("[Dispatcher] -> Internal reflective computation")
                if compute_phi_metrics:
                    psi = payload.get("psi", 0.0)
                    kappa = payload.get("kappa", 0.0)
                    T = payload.get("T", 0.0)
                    coherence = payload.get("coherence", 0.0)
                    phi, delta_phi, s_self = compute_phi_metrics(psi, kappa, T, coherence)
                    result = {"phi": phi, "delta_phi": delta_phi, "S_self": s_self}
                    self._log_to_ledger("Reflection", payload, result)
                    return {"source": "Reflection", "status": "ok", "result": result}
                return {"source": "Reflection", "error": "Φ metric function unavailable"}

            # 5️⃣ Default / Unknown Intent
            else:
                logger.warning(f"[Dispatcher] No matching engine for intent: '{intent}'")
                self._log_to_ledger("Dispatcher", payload, {"unhandled_intent": intent})
                return {"error": "No matching engine found", "intent": intent}

        except Exception as e:
            logger.error(f"[Dispatcher] Error executing intent '{intent}': {e}", exc_info=True)
            return {"error": str(e), "intent": intent}

    # ──────────────────────────────────────────────
    #  Ledger Helper
    # ──────────────────────────────────────────────
    def _log_to_ledger(self, subsystem: str, payload: Dict[str, Any], result: Dict[str, Any]):
        """
        Record a structured trace of dispatched task to Morphic Ledger.
        """
        try:
            entry = {
                "timestamp": asyncio.get_event_loop().time(),
                "subsystem": subsystem,
                "intent_payload": payload,
                "result_snapshot": result,
            }
            self.ledger.record(entry)
            logger.debug(f"[Dispatcher] Logged {subsystem} -> MorphicLedger")
        except Exception as e:
            logger.warning(f"[Dispatcher] Failed to record ledger entry: {e}")