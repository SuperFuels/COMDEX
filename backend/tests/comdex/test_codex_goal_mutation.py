import json
import time
from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.symbolic.codex_ast_parser import parse_codex_ast_from_json
from backend.modules.codex.codex_ast_encoder import encode_codex_ast_to_glyphs
from backend.modules.codex.codex_metrics import CodexMetrics

# 🧪 Sample mutation input
sample_input = {
    "glyph": "g00123-logic",
    "ast": {
        "type": "if",
        "condition": {
            "type": "equals",
            "left": {"type": "var", "name": "x"},
            "right": {"type": "const", "value": 5}
        },
        "then": {
            "type": "assert",
            "expression": {
                "type": "greater_than",
                "left": {"type": "var", "name": "x"},
                "right": {"type": "const", "value": 10}
            }
        }
    },
    "context": {
        "source": "CLI_TEST",
        "container_id": "test-container-123"
    }
}

def run_codex_mutation_test(data):
    executor = CodexExecutor()
    metrics = CodexMetrics()

    print("🧪 Running Codex mutation test...")
    start_time = time.time()

    ast = parse_codex_ast_from_json(data["ast"])
    instruction_tree = encode_codex_ast_to_glyphs(ast)[0].to_instruction_tree()

    context = data.get("context", {})
    context.update({
        "glyph": data["glyph"],
        "ast": ast,
        "source": "CLI_TEST"
    })

    result = executor.execute_instruction_tree(instruction_tree, context=context)
    elapsed = time.time() - start_time

    print(f"\n⏱️ Elapsed: {elapsed:.2f}s")
    print(f"📦 Result Status: {result['status']}")
    print(f"🧠 Raw Result: {json.dumps(result.get('result'), indent=2)}")

    # If contradiction found → track metrics
    if result["status"] == "success" and result["result"].get("status") == "contradiction":
        suggestion = result["result"].get("suggestion")
        print(f"\n🔁 Contradiction detected! Suggested rewrite:")
        print(json.dumps(suggestion, indent=2))

        metrics.record_mutation_test(
            glyph=data["glyph"],
            suggestion=suggestion,
            success=True,
            context=context
        )

if __name__ == "__main__":
    run_codex_mutation_test(sample_input)