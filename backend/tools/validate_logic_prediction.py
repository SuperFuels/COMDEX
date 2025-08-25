import sys
import json
from pathlib import Path

from backend.modules.dna_chain.dc_handler import load_dc_container, save_dc_container
from backend.modules.consciousness.prediction_engine import run_prediction_on_ast
from backend.modules.codex.codex_ast_encoder import encode_codex_ast_to_glyphs
from backend.modules.codex.codex_executor import execute_instruction_tree
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.knowledge_graph.kg_writer_singleton import inject_prediction_trace
from backend.routes.ws.glyphnet_ws import emit_websocket_event

from backend.modules.lean.lean_proofverifier import validate_lean_container
from backend.modules.rewrite.rewrite_executor import suggest_rewrites

# ✅ SQI integration
from backend.modules.sqi.sqi_container_registry import SQIContainerRegistry


def extract_ast_from_container(container) -> dict:
    if "ast" in container:
        return container["ast"]
    elif "glyph_grid" in container:
        return {
            "type": "glyph_program",
            "nodes": container["glyph_grid"]
        }
    elif "electrons" in container:
        return {
            "type": "glyph_program",
            "nodes": [
                glyph for e in container["electrons"] for glyph in e.get("glyphs", [])
            ]
        }
    else:
        raise ValueError("No AST, glyph_grid, or electrons found in container.")


def is_logically_valid(container: dict, container_id: str) -> bool:
    """
    Verifies Lean logic validity. If failed, auto-rewrites container via Codex and sets replay flags.
    Returns True if valid (or successfully fixed), False otherwise.
    """
    valid = validate_lean_container(container, autosave=False)

    if not valid:
        print("❌ Lean verification failed.")
        print("🧬 Attempting auto-rewrite via Codex...")

        rewrites = suggest_rewrites(container)
        if rewrites:
            container["glyphs"] = rewrites
            container.setdefault("metadata", {})["replaySuggested"] = True
            container.setdefault("validation", {})["lean_status"] = "auto_rewritten"
            container.setdefault("mutationTrace", {})["source"] = "lean_autofix"
            print("✅ Applied Codex rewrite. Marked for replay.")
            return True
        else:
            print("⚠️ No valid rewrite found.")
            container.setdefault("validation", {})["lean_status"] = "failed"
            return False
    else:
        container.setdefault("validation", {})["lean_status"] = "valid"
        return True


def validate_logic_prediction(container_path: str, output_trace: bool = False, replay: bool = False):
    print(f"🔍 Loading container: {container_path}")
    container_id = Path(container_path).stem
    container = load_dc_container(container_id)

    try:
        ast = extract_ast_from_container(container)
    except Exception as e:
        print(f"❌ Failed to extract AST: {e}")
        return

    print("🧠 Running prediction engine...")
    result = run_prediction_on_ast(ast)

    if result is None:
        print("⚠️ Prediction returned None — likely unhandled AST or missing kernel.")
        return

    status = result.get("status")
    detail = result.get("detail", "")
    suggestion = result.get("suggestion", {})
    confidence = result.get("confidence", {})
    entropy = result.get("entropy", None)

    print("\n🧪 Prediction Result:")
    if status == "contradiction":
        print(f"❌ CONTRADICTION DETECTED")
        print("Reason:", detail)
    elif status == "simplify":
        print(f"💡 SIMPLIFICATION SUGGESTED")
        print("Suggestion:", suggestion)
    else:
        print(f"✅ LOGIC VALID")
        print("Prediction:", result)

    # 🧠 CodexMetrics log
    CodexMetrics.record_prediction_summary(container_id, [suggestion])

    # 📦 Inject prediction trace into container
    inject_prediction_trace(container, result)

    # 📊 Evaluate SQI Score
    print("\n📊 Evaluating SQI score...")
    sqi_registry = SQIContainerRegistry()
    sqi_info = sqi_registry.evaluate_container(container)
    container.setdefault("validation", {})["sqi_score"] = sqi_info.get("sqi_score", 0.0)
    container["validation"]["sqi_debug"] = sqi_info
    print(f"SQI Score: {sqi_info.get('sqi_score', 0.0):.3f}")
    print("Details:", sqi_info)

    # 🔍 Lean verification + rewrite if needed
    print("\n🔍 Running Lean verification...")
    valid = is_logically_valid(container, container_id)

    # 🔁 Replay Codex logic if container was rewritten
    if replay and (container.get("metadata", {}).get("replaySuggested") or False):
        print("🔁 Running Codex replay with updated logic...")
        try:
            execute_instruction_tree(container)
        except Exception as e:
            print(f"⚠️ Codex replay failed: {e}")

    # 🛰️ WebSocket broadcast
    emit_websocket_event("container_prediction_complete", {
        "containerId": container_id,
        "status": status,
        "trace": result,
        "lean": container.get("validation", {}).get("lean_status", "unknown"),
        "sqi_score": container["validation"].get("sqi_score", 0.0)
    })

    # 💾 Save updated container
    save_dc_container(container_id, container)
    print(f"\n📦 Saved updated container: {container_id}.dc.json")

    # Optional: Write separate trace file
    if output_trace:
        trace_path = container_path.replace(".dc.json", ".trace.json")
        with open(trace_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"📄 Trace written to {trace_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_logic_prediction.py <path_to_dc.json> [--trace] [--replay]")
        sys.exit(1)

    container_path = sys.argv[1]
    save_trace = "--trace" in sys.argv
    replay_codex = "--replay" in sys.argv

    validate_logic_prediction(container_path, output_trace=save_trace, replay=replay_codex)