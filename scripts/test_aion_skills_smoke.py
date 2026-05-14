from backend.modules.aion_skills.registry import get_global_skill_registry, register_builtin_demo_skills
from backend.modules.aion_skills.execution_adapter import SkillExecutionAdapter
from backend.modules.aion_skills.contracts import SkillRunRequest, SkillValidationCase
from backend.modules.aion_skills.validation_harness import SkillValidationHarness
from backend.modules.aion_skills.telemetry import get_global_skill_telemetry


def main() -> None:
    reg = get_global_skill_registry()
    register_builtin_demo_skills(reg)
    adapter = SkillExecutionAdapter(registry=reg)

    # 1) direct run
    req = SkillRunRequest(
        skill_id="skill.echo_text",
        inputs={"text": "hello AION"},
        session_id="kevin-c-smoke",
        turn_id="turn-1",
    ).validate()
    res = adapter.run(req)
    print("direct_run:", res.ok, res.skill_id, res.output)

    # 2) validation harness
    harness = SkillValidationHarness(adapter=adapter)
    case = SkillValidationCase(
        case_id="echo_case_1",
        skill_id="skill.echo_text",
        request=req.to_dict(),
        expected={
            "expect_ok": True,
            "require_output_keys": ["echo", "length"],
            "max_latency_ms": 5000,
        },
        tags=["smoke"],
    ).validate()
    vres = harness.run_case(case)
    print("validation:", vres.ok, vres.pass_rate, vres.checks)

    # 3) telemetry summary
    tel = get_global_skill_telemetry().summary()
    print("telemetry_summary:", tel)

    # 4) registry snapshot count
    snap = reg.to_snapshot()
    print("registry_count:", snap["count"])
    print("skills:", [s["skill_id"] for s in snap["skills"]])


if __name__ == "__main__":
    main()