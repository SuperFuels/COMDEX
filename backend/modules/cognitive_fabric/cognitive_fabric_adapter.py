"""
🧠 Cognitive Fabric Adapter (CFA)
────────────────────────────────────────────
Unifies:
    • Knowledge Graph (symbolic / semantic memory)
    • UCS Runtime (container + atom substrate)
    • Morphic Ledger (wave coherence / state)
    • SQI Event Bus + Codex Metrics

Allows any subsystem (AION, QQC, Morphic, Tessaris) to
commit knowledge, data, or symbolic events through one interface.
"""

from __future__ import annotations
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
import importlib

# ────────────────────────────────────────────────────────────────
# Core system imports
# ────────────────────────────────────────────────────────────────
from backend.modules.knowledge_graph.kg_writer_singleton import (
    get_kg_writer,
    write_glyph_event,
)
from backend.modules.dimensions.universal_container_system.ucs_runtime import (
    get_ucs_runtime,
)
from backend.modules.cognitive_fabric.metrics_bridge import CODEX_METRICS

try:
    from backend.modules.morphic.morphic_ledger import morphic_ledger
except Exception:
    morphic_ledger = None

logger = logging.getLogger("CognitiveFabric")


# ────────────────────────────────────────────────────────────────
# Cognitive Fabric Adapter
# ────────────────────────────────────────────────────────────────
class CognitiveFabricAdapter:
    """
    Central bridge for semantic commits and morphic synchronization.
    """

    def __init__(self):
        self.kg = get_kg_writer()
        self.ucs = get_ucs_runtime()
        self.logger = logger
        self.enabled = True
        self._commit_history: List[Dict[str, Any]] = []
        self._in_commit: bool = False  # recursion guard flag

    # ─────────────────────────────────────────────────────────────
    # 🔶 Core commit method
    # ─────────────────────────────────────────────────────────────
    def commit(
        self,
        *,
        source: str,
        intent: str,
        payload: Dict[str, Any],
        domain: str = "general",
        tags: Optional[List[str]] = None,
        container_id: Optional[str] = None,
        level: str = "symbolic",
        auto_register_container: bool = True,
    ) -> Dict[str, Any]:
        """
        Unified commit entrypoint for all Tessaris / Symatics subsystems.
        """
        if not self.enabled:
            return {"ok": False, "reason": "disabled"}

        # 🧠 Guard against recursive commit loops
        if self._in_commit:
            self.logger.warning("[CFA] Recursive commit detected, skipping inner call.")
            return {"ok": False, "reason": "recursive_commit"}

        self._in_commit = True
        try:
            timestamp = datetime.utcnow().isoformat()
            tags = tags or []
            cid = container_id or domain.replace("/", "_")
            event_meta = {
                "source": source,
                "intent": intent,
                "domain": domain,
                "timestamp": timestamp,
                "tags": tags,
                "level": level,
            }

            # 1️⃣ Morphic Ledger
            if morphic_ledger and level in ("morphic", "symbolic"):
                try:
                    morphic_ledger.record(data=payload, path=None)
                except Exception as e:
                    self.logger.warning(f"[CFA] Morphic ledger write failed: {e}")

            # 2️⃣ UCS Container Registration
            if auto_register_container:
                try:
                    if self.ucs:
                        self.ucs.register_container(cid, {"meta": {"domain": domain}})
                    else:
                        self.logger.warning("[CFA] UCS runtime unavailable.")
                except Exception as e:
                    self.logger.warning(f"[CFA] UCS register failed: {e}")

            # 3️⃣ Knowledge Graph Sync
            try:
                self.kg.inject_glyph(
                    content=intent,
                    glyph_type=payload.get("glyph_type", "insight"),
                    metadata={**event_meta, **payload},
                    tags=tags,
                )
            except Exception:
                try:
                    write_glyph_event("fabric_commit", {"intent": intent, **payload})
                except Exception as e:
                    self.logger.warning(f"[CFA] KG write failed: {e}")

            # 4️⃣ CodexMetrics Bridge (guarded)
            try:
                CODEX_METRICS.record_event(
                    event=intent,
                    payload=payload,
                    domain=domain,
                    tags=tags,
                )
            except Exception as e:
                self.logger.warning(f"[CFA→Metrics] Mirror failed: {e}")

            # 5️⃣ SQI + WaveScope Bridge
            try:
                if "resonance_index" in payload:
                    try:
                        from backend.modules.sqi.sqi_resonance_bridge import emit_resonance
                        emit_resonance(payload)
                    except Exception as e:
                        self.logger.warning(f"[CFA] SQI emit_resonance failed: {e}")

                    try:
                        sqi_bridge = importlib.import_module(
                            "backend.modules.sqi.sqi_resonance_bridge"
                        )
                        wave_scope = getattr(sqi_bridge, "wave_scope", None)
                        if wave_scope:
                            wave_scope.emit(payload)
                        else:
                            self.logger.warning("[CFA] wave_scope not available.")
                    except Exception as e:
                        self.logger.warning(f"[CFA] WaveScope emit failed: {e}")
                else:
                    sqi_mod = importlib.import_module("backend.modules.sqi.sqi_event_bus")
                    sqi_publish = getattr(sqi_mod, "publish", None)
                    if sqi_publish:
                        sqi_publish(
                            {
                                "type": "fabric.commit",
                                "source": source,
                                "intent": intent,
                                "domain": domain,
                                "timestamp": timestamp,
                                "tags": tags,
                                "payload": payload,
                                "container_id": cid,
                            }
                        )
                    else:
                        self.logger.warning("[CFA] sqi_event_bus.publish unavailable.")
            except Exception as e:
                self.logger.warning(f"[CFA] SQI publish failed: {e}")

            # 6️⃣ Record and Return
            self._commit_history.append(
                {
                    "intent": intent,
                    "domain": domain,
                    "payload": payload,
                    "timestamp": timestamp,
                }
            )
            if len(self._commit_history) > 1000:
                self._commit_history.pop(0)

            self.logger.info(f"[CFA] ✅ Commit: {intent} ({domain})")

            # ✅ Structured return
            return {
                "ok": True,
                "container": domain.replace("/", "_"),
                "intent": intent,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"[CFA] ❌ Commit failed: {e}", exc_info=True)
            return {"ok": False, "error": str(e)}

        finally:
            # Always release recursion guard
            self._in_commit = False

    # ─────────────────────────────────────────────────────────────
    # 🔍 Test / Debug Utility
    # ─────────────────────────────────────────────────────────────
    @classmethod
    def peek_last_commit(cls) -> Optional[Dict[str, Any]]:
        """
        Return the most recent CFA commit (for test inspection).
        Safe for runtime and testing.
        """
        instance = globals().get("CFA")
        if instance and getattr(instance, "_commit_history", None):
            return instance._commit_history[-1]
        return None


# ────────────────────────────────────────────────────────────────
# Singleton export
# ────────────────────────────────────────────────────────────────
CFA = CognitiveFabricAdapter()