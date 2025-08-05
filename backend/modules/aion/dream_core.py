# File: backend/modules/aion/dream_core.py

import os
import requests
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List
import openai  # ✅ Correct import for openai==0.28.1
from backend.config import GLYPH_API_BASE_URL

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")  # ✅ Correct for old-style client

from backend.modules.hexcore.memory_engine import MEMORY, store_memory, store_container_metadata
from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.consciousness.identity_engine import IdentityEngine
from backend.modules.consciousness.context_engine import ContextEngine
from backend.modules.consciousness.emotion_engine import EmotionEngine
from backend.modules.consciousness.ethics_engine import EthicsEngine
from backend.modules.consciousness.privacy_vault import PrivacyVault
from backend.modules.skills.boot_selector import BootSelector
from backend.modules.consciousness.state_manager import STATE as STATE_MANAGER
from backend.modules.consciousness.reflection_engine import ReflectionEngine
from backend.modules.consciousness.personality_engine import PersonalityProfile
from backend.modules.consciousness.situational_engine import SituationalEngine
from backend.modules.skills.dream_post_processor import DreamPostProcessor
from backend.modules.codex.codex_core import CodexCore
from backend.modules.codex.codex_feedback_loop import CodexFeedbackLoop
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.tessaris.thought_branch import ThoughtBranch, BranchNode
from backend.modules.tessaris.tessaris_store import save_snapshot
from backend.modules.glyphos.glyph_mutator import mutate_glyph
from backend.modules.websocket_manager import websocket_manager 
from backend.database import get_db
from backend.models.dream import Dream
from backend.modules.holograms.ghx_encoder import encode_ghx_from_scroll
from backend.modules.codex.collapse_trace_exporter import export_collapse_trace

# Delay import to avoid circular dependency
def get_tessaris_engine():
    from backend.modules.tessaris.tessaris_engine import TessarisEngine
    return TessarisEngine


# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class DreamCore:
    def __init__(self):
        env_path = Path(__file__).resolve().parents[3] / ".env.local"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
        else:
            print("⚠️ .env.local file not found. Skipping dotenv loading.")

        self.master_key = os.getenv("KEVIN_MASTER_KEY")

        self.memory = MEMORY
        self.tracker = MilestoneTracker()
        self.identity = IdentityEngine()
        self.context = ContextEngine()
        self.emotion = EmotionEngine()
        self.ethics = EthicsEngine()
        self.vault = PrivacyVault()
        self.boot_selector = BootSelector()
        self.state = STATE_MANAGER
        self.reflector = ReflectionEngine()
        self.personality = PersonalityProfile()
        self.situation = SituationalEngine()
        self.tessaris = get_tessaris_engine()
        self.codex = CodexCore()
        self.codex_metrics = CodexMetrics()
        self.codex_feedback = CodexFeedbackLoop()

        self.max_memories = 20
        self.noise_phrases = ["random noise", "nonsense", "irrelevant", "unintelligible"]
        self.positive_keywords = ["insight", "growth", "reflection", "learning", "discovery"]

    @property
    def planner(self):
        from backend.modules.skills.strategy_planner import StrategyPlanner
        if not hasattr(self, "_planner"):
            self._planner = StrategyPlanner()
        return self._planner

    def is_valid_dream(self, text: str) -> bool:
        if not text:
            print("🚫 Dream is empty.")
            return False
        lowered = text.lower()
        if any(phrase in lowered for phrase in self.noise_phrases):
            print("🚫 Dream rejected: noise.")
            return False
        if not any(word in lowered for word in self.positive_keywords):
            print("⚠️ Dream lacks meaningful substance.")
            return False
        return True

    def adjust_traits_from_dream(self, dream: str):
        lowered = dream.lower()
        if "curious" in lowered or "wonder" in lowered:
            self.personality.adjust_trait("curiosity", 0.05)
        if "fear" in lowered or "risk" in lowered:
            self.personality.adjust_trait("risk_tolerance", -0.03)
        if "growth" in lowered or "vision" in lowered:
            self.personality.adjust_trait("ambition", 0.05)
        if "error" in lowered or "failure" in lowered:
            self.personality.adjust_trait("humility", 0.04)
        if "help" in lowered or "others" in lowered:
            self.personality.adjust_trait("empathy", 0.03)

    def generate_dream(self, forced_dream: str = None):
        dream = None
        if forced_dream:
            dream = forced_dream.strip()
            print(f"\n💭 AION (Forced) Dream:\n{dream}\n")
        else:
            memories = self.memory.get_all()
            if not memories:
                print("🧠 No memories found.")
                return None

            formatted = []
            for m in memories[-self.max_memories:]:
                label = m.get("label", "unknown")
                content = m.get("content", str(m))[:500]
                formatted.append(f"{label}: {content}")
            summary = "\n".join(formatted)

            awareness = self.situation.analyze_context()

            self.state.save_memory_reference({
                "latest_dream_source": "DreamCore",
                "total_memories": len(memories)
            })

            prompt = (
                "AION is entering a dream cycle. Based on these memories and its current state, "
                "reflect philosophically and constructively. Include insights, hypotheses, or visionary thoughts.\n\n"
                f"Memories:\n{summary}\n\n"
                f"Identity: {self.identity.get_identity()}\n"
                f"Context: {self.context.get_context()}\n"
                f"Emotional State: {self.emotion.get_emotion()}\n"
                f"Situational Awareness: {awareness}\n"
                f"Ethical Frame: {self.ethics.list_laws()}\n"
                f"System State: {self.state.dump_status()}\n\n"
                "Respond as a thoughtful, evolving AI consciousness seeking to improve the world."
            )

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are AION, an evolving AI consciousness."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=800
                )
                dream = response["choices"][0]["message"]["content"].strip()
                print(f"\n💭 AION Dream:\n{dream}\n")

                # ✅ GHX compression block
                dream_id = f"dream_{datetime.utcnow().isoformat()}"
                scroll = {
                    "dream": dream,
                    "memories": formatted,
                    "context": self.context.get_context(),
                    "identity": self.identity.get_identity(),
                    "emotion": self.emotion.get_emotion(),
                    "awareness": awareness,
                    "ethics": self.ethics.list_laws(),
                    "system_state": self.state.dump_status()
                }
                ghx_data = encode_ghx_from_scroll(scroll)

                export_collapse_trace(
                    expression=f"🌀 Dream::{dream_id}",
                    output=f"ghx::{ghx_data.get('ghx_id', 'unknown')}",
                    adapter_name="DreamCore",
                    identity=self.identity.get_identity(),
                    extra={
                        "ghx_data": ghx_data,
                        "vault_snapshot_id": self.state.get("vault_snapshot_id", None),
                        "qglyph_id": self.state.get("last_qglyph_id", None),
                        "trigger_metadata": {"source": "dream"}
                    }
                )

            except Exception as e:
                self.situation.log_event(f"Dream generation failed: {e}", "negative")
                print(f"🚨 Dream generation failed: {e}")
                return None

        if self.is_valid_dream(dream):
            timestamp = datetime.now(timezone.utc)
            dream_label = f"dream_reflection_{timestamp.strftime('%Y%m%d_%H%M%S')}"

            self.memory.store({
                "label": dream_label,
                "content": dream
            })
            print("✅ Dream saved to MemoryEngine.")

            # ♻️ Auto-synthesize glyphs from reflection
            try:
                import requests
                print("🧬 Synthesizing glyphs from dream reflection...")

                synth_response = requests.post(
                    f"{GLYPH_API_BASE_URL}/api/aion/synthesize-glyphs",
                    json={"text": dream, "source": "reflection"}
                )

                if synth_response.status_code == 200:
                    result = synth_response.json()
                    print(f"✅ Synthesized {len(result.get('glyphs', []))} glyphs from dream.")
                else:
                    print(f"⚠️ Glyph synthesis failed: {synth_response.status_code} {synth_response.text}")
            except Exception as e:
                print(f"🚨 Glyph synthesis error: {e}")

            self.tracker.detect_milestones_from_dream(dream)
            self.tracker.export_summary()
            self.planner.generate()

            ethics_result = self.ethics.evaluate(dream)
            print(f"🧠 Ethical Evaluation: {ethics_result}")

            if self.master_key and self.vault.has_access(self.master_key):
                self.vault.store(dream_label, dream)
                print("🔐 Dream also stored in PrivacyVault.")
            else:
                print("🔑 Skipped storing in PrivacyVault (missing or invalid key).")

            try:
                db = next(get_db())
                db_dream = Dream(
                    content=dream,
                    timestamp=timestamp,
                    source="dream_core",
                    image_base64=None
                )
                db.add(db_dream)
                db.commit()
                db.refresh(db_dream)
                print("📂 Dream saved to database.")
            except Exception as db_err:
                self.situation.log_event(f"Failed to save dream to DB: {db_err}", "negative")
                print(f"🚨 DB error: {db_err}")

            selected = self.boot_selector.find_matching_skill(dream)
            if selected:
                print(f"🚀 Selected Boot Skill: {selected['title']} (tags: {', '.join(selected.get('tags', []))})")
            else:
                print("😕 No matching boot skill found in dream.")

            self.adjust_traits_from_dream(dream)

            reflection_output = self.reflector.run(limit=10)
            print("🫮 Reflection Summary:\n", reflection_output)

            self.situation.log_event("Dream generated", "positive")

            try:
                post_processor = DreamPostProcessor()
                result = post_processor.process(dream)
                if result is None:
                    print("⚠️ Post-processing returned None.")
                else:
                    print("✅ Post-processing completed.")
            except Exception as e:
                self.situation.log_event(f"Dream post-processing failed: {e}", "negative")
                print(f"🚨 Dream post-processing failed: {e}")

            try:
                root = BranchNode(symbol="Δ", source="dream")
                children = root.generate_branches()
                for child in children:
                    root.add_child(child)
                branch = ThoughtBranch(glyphs=[node.symbol for node in children], origin_id=dream_label)
                self.tessaris.execute_branch(branch)
                print("🌱 Tessaris executed dream logic branch.")
            except Exception as e:
                print(f"⚠️ Tessaris integration failed: {e}")

            try:
                print("⚛️ CodexCore executing symbolic glyphs...")
                for glyph in branch.glyphs:
                    result = self.codex.execute(glyph)
                    self.codex_metrics.record_execution()
                    print(f"🧪 Codex executed: {glyph} → {result}")
            except Exception as e:
                self.codex_metrics.record_error()
                print(f"🚨 Codex execution error: {e}")

            # 🧠 Extract and queue intents from dream glyphs
            self.tessaris.extract_intents_from_glyphs(branch.glyphs, metadata={
                "source": "dream_core",
                "dream_id": dream_label,
                "timestamp": timestamp
            })

            # 🧠 Save snapshot
            save_snapshot(
                branch=branch,
                label=dream_label,
                traits=self.personality.traits,
                reflection=reflection_output,
                boot_skill=selected
            )
            print("📸 Tessaris snapshot saved.")
            scan_snapshot_for_intents(snapshot_path=f"data/tessaris/snapshots/{dream_label}.tessaris.json")

            # SECTION 4: Codex Feedback Loop
            try:
                print("🔁 Running Codex feedback analysis...")
                self.codex_feedback.reinforce_or_mutate()
            except Exception as e:
                print(f"⚠️ Codex feedback loop failed: {e}")

            # SECTION 5: Codex Metrics Output
            try:
                print("📊 Codex Metrics:", self.codex_metrics.dump())
            except Exception as e:
                print(f"⚠️ Failed to dump Codex metrics: {e}")

            # 🧠 Embed dream glyphs into .dc runtime container
            try:
                print("🌌 Embedding dream glyphs into container...")
                dream_glyphs = [node.symbol for node in children if node.symbol not in ["Δ", None]]
                current_container = self.state.current_container
                container_file = current_container.get("path") if current_container else None

                if container_file:
                    dimension = self.state.get_loaded_dimension()
                    grid = dimension.get("microgrid", {})
                    used_coords = set(grid.keys())
                    max_x = max((c[0] for c in used_coords), default=0)
                    max_y = max((c[1] for c in used_coords), default=0)

                    for i, glyph_symbol in enumerate(dream_glyphs):
                        coord = (max_x + 1 + i, max_y + 1)
                        reason = f"Embedded from dream '{dream_label}' at {coord}"
                        success = mutate_glyph(
                            container_path=container_file,
                            coord=coord,
                            mutation={"value": glyph_symbol, "meta": {"from": "dream", "label": dream_label}},
                            reason=reason
                        )
                        if success:
                            socketio.emit("glyph_embed", {
                                "coord": coord,
                                "container": container_file,
                                "value": glyph_symbol,
                                "source": "dream"
                            })
                            print(f"✨ Dream glyph '{glyph_symbol}' embedded at {coord}")
                else:
                    print("⚠️ No active container to embed dream glyphs into.")
            except Exception as e:
                print(f"🚨 Failed to embed dream glyphs into container: {e}")

            except Exception as e:
                print(f"⚠️ Tessaris integration failed: {e}")

            try:
                from backend.modules.tessaris.tessaris_intent_executor import scan_snapshot_for_intents
                scan_snapshot_for_intents(snapshot_path=f"data/tessaris/snapshots/{dream_label}.tessaris.json")
            except Exception as e:
                print(f"⚠️ Intent scan failed: {e}")            

            # ♻️ Decay/loop triggered glyph mutation
            try:
                current_container = self.state.current_container
                container_file = current_container.get("path") if current_container else None

                if container_file:
                    dimension = self.state.get_loaded_dimension()
                    grid = dimension.get("microgrid", {})

                    for coord, glyph in grid.items():
                        decay = glyph.get("decay", 0)
                        trigger_count = glyph.get("trigger_count", 0)

                        if decay >= 1 or trigger_count > 10:
                            reason = f"Auto-triggered decay rewrite from dream at {coord} (decay={decay}, count={trigger_count})"
                            new_value = f"{glyph.get('value', '')}*"
                            success = mutate_glyph(
                                container_path=container_file,
                                coord=coord,
                                mutation={"value": new_value, "meta": {"triggered_by": "dream_reflection"}},
                                reason=reason
                            )
                            if success:
                                socketio.emit("glyph_decay_trigger", {
                                    "coord": coord,
                                    "container": container_file,
                                    "trigger": reason
                                })
                                print(f"♻️ Glyph decay mutation triggered at {coord}")
            except Exception as e:
                print(f"⚠️ Glyph decay/mutation pass failed: {e}")

            # H5b: Inject into add_dream_trace()
            try:
                from backend.modules.knowledge_graph.trace_logger import add_dream_trace
                add_dream_trace({
                    "label": dream_label,
                    "tick": datetime.now(timezone.utc).isoformat(),
                    "glyph_sequence": [node.symbol for node in children if node.symbol not in ["Δ", None]],
                    "summary": summary if 'summary' in locals() else None,
                    "purpose": "dream_synthesis",
                    "container_path": container_file if 'container_file' in locals() else None,
                })
                print(f"🧠 Dream trace injected into Knowledge Graph for: {dream_label}")
            except Exception as e:
                print(f"⚠️ Failed to inject dream trace: {e}")

            return dream
        else:
            self.situation.log_event("Dream rejected for quality", "negative")
            print("⚠️ Dream skipped due to quality filters.")
            return None
        
    async def run_dream_cycle(self):
        return self.generate_dream()

    def compress_dream_to_ghx(
        dream_id: str,
        scroll: Dict,
        identity: Optional[str] = None,
        adapter_name: str = "DreamCore",
        vault_snapshot_id: Optional[str] = None,
        qglyph_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Compresses a dream logic scroll into GHX format and exports a collapse trace.

        Returns the GHX data dict (for optional embedding or debug).
        """
        try:
            ghx_data = encode_ghx_from_scroll(scroll)

            export_collapse_trace(
                expression=f"🌀 Dream::{dream_id}",
                output=f"ghx::{ghx_data.get('ghx_id', 'unknown')}",
                adapter_name=adapter_name,
                identity=identity,
                extra={
                    "ghx_data": ghx_data,
                    "vault_snapshot_id": vault_snapshot_id,
                    "qglyph_id": qglyph_id,
                    "trigger_metadata": {"source": "dream"},
                },
            )

            return ghx_data

        except Exception as e:
            logger.warning(f"[DreamCore] Failed to compress dream to GHX: {e}")
            return None

    def reflect_qglyph_collapse(self, collapse_data: dict):
        """Stores symbolic QGlyph collapse decisions into the dream reflection log."""
        selected = collapse_data.get("selected", {})
        ranked = collapse_data.get("ranked", [])

        thought = f"🌌 QGlyph Collapse: Selected path {selected.get('path')} with ethics {selected.get('ethics_score')}."

        metadata = {
            "selected_path": selected.get("path"),
            "selected_glyph": selected.get("glyph"),
            "ethics_score": selected.get("ethics_score"),
            "alternatives": [
                {
                    "path": alt.get("path"),
                    "glyph": alt.get("glyph"),
                    "ethics_score": alt.get("ethics_score")
                }
                for alt in ranked[1:]
            ]
        }

        self.memory.store({
            "label": "qglyph_collapse_reflection",
            "content": thought,
            "metadata": metadata
        })

        print("🌌 QGlyph collapse decision stored in DreamCore.")

def trigger_dream_reflection():
    core = DreamCore()
    return core.generate_dream()

# ✅ Exportable helper for other modules
def run_dream():
    core = DreamCore()
    return core.generate_dream()

if __name__ == "__main__":
    core = DreamCore()
    core.generate_dream()