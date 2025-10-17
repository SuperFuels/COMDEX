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
import datetime
import logging
from typing import Any, Dict, List, Optional

# ────────────────────────────────────────────────────────────────
# Core system imports
# ────────────────────────────────────────────────────────────────
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer, write_glyph_event
from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime
from backend.modules.sqi.sqi_event_bus import publish as sqi_publish

try:
    from backend.modules.codex.codex_metrics import codex_metrics
except Exception:
    codex_metrics = None

try:
    from backend.modules.morphic.morphic_ledger import morphic_ledger
except Exception:
    morphic_ledger = None


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
        self.logger = logging.getLogger("CognitiveFabric")
        self.enabled = True

        # 🧩 Add commit history buffer for test visibility
        self._commit_history: List[Dict[str, Any]] = []

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
        The unified commit entrypoint.

        Args:
            source: Subsystem name (AION, QQC, etc.)
            intent: Short description of what’s being committed
            payload: Arbitrary data to store or link
            domain: Logical namespace (symatics, physics, etc.)
            tags: Optional classification tags
            container_id: Optional target container
            level: 'symbolic' | 'morphic' | 'runtime'
        """
        if not self.enabled:
            return {"ok": False, "reason": "disabled"}

        timestamp = datetime.datetime.utcnow().isoformat()
        event_meta = {
            "source": source,
            "intent": intent,
            "domain": domain,
            "timestamp": timestamp,
            "tags": tags or [],
            "level": level,
        }

        try:
            # ── 1️⃣ Morphic Ledger recording
            if morphic_ledger and level in ("morphic", "symbolic"):
                try:
                    morphic_ledger.record(
                        intent=intent,
                        data=payload,
                        domain=domain,
                        meta=event_meta,
                    )
                except Exception as e:
                    self.logger.warning(f"[CFA] Morphic ledger write failed: {e}")

            # ── 2️⃣ UCS container integration
            cid = container_id or domain.replace("/", "_")
            if auto_register_container:
                try:
                    self.ucs.register_container(cid, {"meta": {"domain": domain}})
                except Exception as e:
                    self.logger.warning(f"[CFA] UCS register failed for {cid}: {e}")

            # Optional atom creation if symbolic content exists
            atom = {
                "id": f"{intent}_{int(datetime.datetime.utcnow().timestamp())}",
                "type": "atom",
                "meta": {"domain": domain, "intent": intent, "source": source},
                "caps": list(payload.get("caps", [])),
                "nodes": list(payload.get("nodes", [])),
                "tags": tags or [],
            }
            try:
                self.ucs.register_atom(cid, atom)
            except Exception as e:
                self.logger.warning(f"[CFA] register_atom failed: {e}")

            # ── 3️⃣ Knowledge Graph write
            try:
                self.kg.inject_glyph(
                    content=intent,
                    glyph_type=payload.get("glyph_type", "insight"),
                    metadata={**event_meta, **payload},
                    tags=tags or [],
                )
            except Exception:
                # fallback legacy write_glyph_event if inject_glyph unavailable
                try:
                    write_glyph_event("fabric_commit", {"intent": intent, **payload})
                except Exception as e:
                    self.logger.warning(f"[CFA] KG write failed: {e}")

            # ── 4️⃣ Metrics + SQI bus broadcast
            event_packet = {
                "type": "fabric.commit",
                "source": source,
                "intent": intent,
                "domain": domain,
                "timestamp": timestamp,
                "tags": tags or [],
                "payload": payload,
                "container_id": cid,
            }

            if codex_metrics:
                try:
                    codex_metrics.record_event("fabric_commit", event_packet)
                except Exception as e:
                    self.logger.warning(f"[CFA] codex_metrics record failed: {e}")

            try:
                sqi_publish(event_packet)
            except Exception as e:
                self.logger.warning(f"[CFA] SQI publish failed: {e}")

            # ✅ Record commit in local memory (for testing)
            self._commit_history.append(event_packet)
            if len(self._commit_history) > 1000:
                self._commit_history.pop(0)

            self.logger.info(f"[CFA] ✅ Commit: {intent} ({domain})")
            return {"ok": True, "container": cid, "intent": intent, "timestamp": timestamp}

        except Exception as e:
            self.logger.error(f"[CFA] ❌ Commit failed: {e}", exc_info=True)
            return {"ok": False, "error": str(e)}

    # ─────────────────────────────────────────────────────────────
    # 🔍 Test / Debug Utility
    # ─────────────────────────────────────────────────────────────
    @classmethod
    def peek_last_commit(cls) -> Optional[Dict[str, Any]]:
        """
        Return the most recent CFA commit (for test inspection).
        Safe for both runtime and pytest environments.
        """
        instance = globals().get("CFA")
        if instance and hasattr(instance, "_commit_history") and instance._commit_history:
            return instance._commit_history[-1]
        return None


# ────────────────────────────────────────────────────────────────
# Singleton export
# ────────────────────────────────────────────────────────────────
CFA = CognitiveFabricAdapter()