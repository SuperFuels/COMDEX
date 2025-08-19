# tools/batch_predict_containers.py

import os
import json
import time
from pathlib import Path
from typing import Dict, Any

from backend.modules.teleport.vault_bridge import load_dc_container
from backend.modules.consciousness.prediction_engine import PredictionEngine
from backend.modules.symbolic.soul_law_validator import is_soullaw_locked
from backend.modules.codex.codex_executor import execute_instruction_tree
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.glyphnet.glyphnet_ws import emit_websocket_event
from backend.modules.knowledge_graph.knowledge_graph_writer import save_container_to_disk

# Toggle features
ENABLE_GLYPHNET_BROADCAST = True
ENABLE_VAULT_SAVE = True
ENABLE_CODEX_REPLAY = True

engine = PredictionEngine()


def inject_confidence_summary(container: Dict[str, Any], rewrites: list):
    if not rewrites:
        return

    summary = {
        "max_entropy_delta": max(r.get("entropy_delta", 0) for r in rewrites),
        "avg_goal_match_score": sum(r.get("goal_match_score", 0) for r in rewrites) / len(rewrites),
        "max_rewrite_success_prob": max(r.get("rewrite_success_prob", 0) for r in rewrites),
        "valid_rewrites": sum(1 for r in rewrites if r.get("logically_valid")),
    }
    container.setdefault("traceMetadata", {})["predictionConfidenceSummary"] = summary


def process_container(path: Path):
    try:
        with open(path) as f:
            container = json.load(f)

        container_id = container.get("id") or path.stem

        # 🔒 SoulLaw lock check
        if is_soullaw_locked(container):
            print(f"🔒 SKIPPED: {container_id} (SoulLaw locked)")
            return

        print(f"🧠 Predicting: {container_id}")
        result = engine.run_prediction_on_container(container)

        rewrites = result.get("rewrites", [])

        inject_confidence_summary(container, rewrites)

        # 🔁 Auto Codex replay on strong rewrites
        if ENABLE_CODEX_REPLAY:
            should_replay = any(r.get("rewrite_success_prob", 0) > 0.8 and r.get("logically_valid") for r in rewrites)
            if should_replay:
                print(f"🔁 Replaying container: {container_id}")
                try:
                    execute_instruction_tree(container)
                except Exception as e:
                    print(f"⚠️ Codex replay error in {container_id}: {e}")

        # 🧠 Metrics
        CodexMetrics.record_prediction_summary(container_id, rewrites)

        # ☁️ Sync to GlyphNet
        if ENABLE_GLYPHNET_BROADCAST:
            emit_websocket_event("container_prediction_complete", {
                "containerId": container_id,
                "status": result.get("status", "ok"),
                "prediction": rewrites,
            })

        # 💾 Save predictions to Vault
        if ENABLE_VAULT_SAVE:
            out_path = Path(f"vault/predicted/{path.name}")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as out:
                json.dump(container, out, indent=2)
            print(f"📦 Saved: {out_path}")

    except Exception as e:
        print(f"❌ Error in {path.name}: {e}")


def run_batch_prediction():
    base_path = Path("containers/")
    if not base_path.exists():
        print("❌ No containers directory found.")
        return

    paths = list(base_path.glob("*.dc.json"))
    if not paths:
        print("⚠️ No containers to process.")
        return

    for path in paths:
        process_container(path)


if __name__ == "__main__":
    print("🔍 Running batch prediction on containers...")
    run_batch_prediction()
    print("✅ Batch complete.")