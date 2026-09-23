# File: backend/photon_algebra/tests/manual_registry_magnetism_smoke.py

from backend.core.registry_bridge import registry_bridge
from backend.modules.codex.codex_executor import execute_photon_capsule


def main() -> None:
    exprs = [
        {"op": "⊕", "states": ["a", "b"]},
        {"op": "⊗", "states": ["a", "b"]},
        {"op": "↔", "states": ["a", "b"]},
    ]

    expected = {
        "⊕": {
            "semantic_label": "superposed_field",
            "magnetic_mode": "distributed_interference",
            "fallback_symbol_id": "S1",
        },
        "⊗": {
            "semantic_label": "fused_field",
            "magnetic_mode": "constructive_lock",
            "fallback_symbol_id": "S1",
        },
        "↔": {
            "semantic_label": "entangled_alignment",
            "magnetic_mode": "coupled_alignment",
            "fallback_symbol_id": "S2",
        },
    }

    for expr in exprs:
        op = expr["op"]
        rule = expected[op]

        print("\n" + "=" * 60)
        print("EXPR:", expr)

        print("\n--- registry: photon:magnetic_intent ---")
        intent = registry_bridge.resolve_and_execute(
            "photon:magnetic_intent",
            expr=expr,
        )
        assert isinstance(intent, dict)
        assert intent["semantic_label"] == rule["semantic_label"]
        assert intent["magnetic_intent"]["mode"] == rule["magnetic_mode"]

        print("semantic_label:", intent["semantic_label"])
        print("symbol_hint:", intent["symbol_hint"])
        print("magnetic_mode:", intent["magnetic_intent"]["mode"])

        print("\n--- registry: photon:compile_field_program ---")
        compiled = registry_bridge.resolve_and_execute(
            "photon:compile_field_program",
            expr=expr,
            fallback_symbol_id=rule["fallback_symbol_id"],
        )
        assert isinstance(compiled, dict)
        assert compiled["program"]["metadata"]["magnetic_mode"] == rule["magnetic_mode"]

        print("program_symbol_id:", compiled["program"]["symbol_id"])
        print("program_mode:", compiled["program"]["metadata"]["magnetic_mode"])

        print("\n--- codex_executor.execute_photon_capsule ---")

        glyph_entry = {
            "operator": op,
            "name": f"expr_{op}",
        }

        if "states" in expr:
            glyph_entry["args"] = list(expr["states"])
        elif "state" in expr:
            glyph_entry["args"] = [expr["state"]]
        else:
            glyph_entry["args"] = []

        capsule = {
            "name": f"magnetism_capsule_{op}",
            "glyphs": [glyph_entry],
        }

        capsule_result = execute_photon_capsule(
            capsule,
            context={
                "capsule_id": f"test_capsule_{op}",
                "compile_field_program": True,
                "fallback_symbol_id": rule["fallback_symbol_id"],
                "field_amplitude": 1.0,
                "field_frequency": 1.0,
                "photon_expr": expr,
                "source": "photon",
            },
        )

        assert isinstance(capsule_result, dict)
        assert capsule_result["status"] == "success"
        assert "magnetic_bridge" in capsule_result
        assert isinstance(capsule_result["magnetic_bridge"], dict)

        bridge = capsule_result["magnetic_bridge"]
        assert bridge["intent"]["semantic_label"] == rule["semantic_label"]
        assert bridge["intent"]["magnetic_intent"]["mode"] == rule["magnetic_mode"]

        if "program" in bridge:
            assert bridge["program"]["metadata"]["magnetic_mode"] == rule["magnetic_mode"]
            assert bridge["program"]["symbol_id"] == rule["fallback_symbol_id"]

        print("capsule_engine:", capsule_result["engine"])
        print("capsule_semantic_label:", bridge["intent"]["semantic_label"])
        print("capsule_magnetic_mode:", bridge["intent"]["magnetic_intent"]["mode"])
        if "program" in bridge:
            print("capsule_program_symbol_id:", bridge["program"]["symbol_id"])
            print("capsule_program_mode:", bridge["program"]["metadata"]["magnetic_mode"])

    print("\nOK: registry + codex executor magnetism smoke test passed")


if __name__ == "__main__":
    main()