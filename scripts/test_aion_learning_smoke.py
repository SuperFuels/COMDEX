from __future__ import annotations

import os

from backend.modules.aion_skills.contracts import SkillRunRequest
from backend.modules.aion_skills.registry import get_global_skill_registry, register_builtin_demo_skills
from backend.modules.aion_skills.execution_adapter import SkillExecutionAdapter
from backend.modules.aion_learning.runtime import get_aion_learning_runtime


def main() -> None:
    reg = get_global_skill_registry()
    register_builtin_demo_skills(reg)

    adapter = SkillExecutionAdapter()
    learning = get_aion_learning_runtime()

    # Optional clean-ish visibility note (does not delete file)
    print("learning_events_path:", learning.events_path)
    print("learning_weaknesses_path:", learning.weaknesses_path)

    # Success runs
    r1 = adapter.run(
        SkillRunRequest(
            skill_id="skill.echo_text",
            inputs={"text": "hello"},
            session_id="phase-d-smoke",
            turn_id="t1",
            request_id="req-1",
        )
    )
    r2 = adapter.run(
        SkillRunRequest(
            skill_id="skill.aion_roadmap_priority",
            inputs={"topic": "AION roadmap"},
            session_id="phase-d-smoke",
            turn_id="t2",
            request_id="req-2",
        )
    )

    # Fail runs (intentional)
    r3 = adapter.run(
        SkillRunRequest(
            skill_id="skill.does_not_exist",
            inputs={},
            session_id="phase-d-smoke",
            turn_id="t3",
            request_id="req-3",
        )
    )
    r4 = adapter.run(
        SkillRunRequest(
            skill_id="skill.does_not_exist",
            inputs={},
            session_id="phase-d-smoke",
            turn_id="t4",
            request_id="req-4",
        )
    )

    # Another success
    r5 = adapter.run(
        SkillRunRequest(
            skill_id="skill.echo_text",
            inputs={"text": "phase d"},
            session_id="phase-d-smoke",
            turn_id="t5",
            request_id="req-5",
        )
    )

    print("runs_ok:", [r1.ok, r2.ok, r3.ok, r4.ok, r5.ok])
    print("error_codes:", [r.error_code for r in [r1, r2, r3, r4, r5]])

    # Summaries
    summary = learning.summarize()
    weaknesses = learning.detect_weaknesses(persist=True)
    report = learning.get_weakness_report()

    print("summary_total_events:", summary.get("total_events"))
    print("summary_ok_fail:", summary.get("ok_count"), summary.get("fail_count"))
    print("summary_avg_process_score:", summary.get("avg_process_score"))
    print("summary_avg_reward_score:", summary.get("avg_reward_score"))
    print("summary_by_skill_keys:", sorted(list((summary.get("by_skill") or {}).keys())))

    print("weakness_count:", len(weaknesses))
    if weaknesses:
        print("top_weakness:", weaknesses[0].to_dict())

    print("report_count:", report.get("count"))
    print("events_file_exists:", os.path.exists(learning.events_path))
    print("weakness_file_exists:", os.path.exists(learning.weaknesses_path))

    smoke_ok = bool(os.path.exists(learning.events_path)) and summary.get("total_events", 0) >= 1
    print("learning_smoke_ok:", smoke_ok)


if __name__ == "__main__":
    main()