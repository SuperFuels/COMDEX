from __future__ import annotations

from backend.modules.aion_learning.runtime import get_aion_learning_runtime
from backend.modules.aion_learning.contracts import AionLearningQuery


def main() -> None:
    rt = get_aion_learning_runtime()

    print("learning_events_path:", rt.paths.events_path)
    print("learning_weaknesses_path:", rt.paths.weaknesses_path)

    # Typed query
    q = AionLearningQuery(limit=50, include_weaknesses=True).validate()

    summary = rt.build_summary(q)
    print("summary_total_events:", summary.total_events)
    print("summary_ok_fail:", summary.ok_count, summary.fail_count)
    print("summary_avg_process_score:", round(summary.avg_process_score, 4))
    print("summary_avg_outcome_score:", round(summary.avg_outcome_score, 4))
    print("summary_avg_reward_score:", round(summary.avg_reward_score, 4))

    report = rt.build_report(q)
    print("report_id:", report.report_id)
    print("report_top_weaknesses:", len(report.top_weaknesses))
    print("report_recent_events:", len(report.recent_events))

    ctx = rt.get_learning_context_view(topic="AION roadmap", query=q)
    ctxd = ctx.to_dict()
    print("context_schema:", ctxd.get("schema_version"))
    print("context_writable:", ctxd.get("writable"))
    print("context_summary:", ctxd.get("summary"))
    print("context_weakness_hints_count:", len(ctxd.get("weakness_hints", [])))
    print("context_cautions_count:", len(ctxd.get("recommended_cautions", [])))

    ok = (
        ctxd.get("writable") is False
        and "avg_reward_score" in (ctxd.get("summary") or {})
        and isinstance(report.top_weaknesses, list)
    )
    print("learning_sprint2_smoke_ok:", ok)


if __name__ == "__main__":
    main()