"""Read-only progress projection for AION native English intelligence."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time
from typing import Any

from backend.modules.aion_cognition.native_english_teacher import CURRICULUM
from backend.modules.aion_cognition.native_lexical_intelligence import default_database_path
from backend.modules.hexcore.progressive_competency_system import ProgressiveCompetencySystem


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _recent_cycles(path: Path, limit: int = 8) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[-max(1, limit):]
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        exam = payload.get("closed_book_exam") or {}
        stage = payload.get("stage") or {}
        rows.append({
            "stage_id": stage.get("id"), "stage_title": stage.get("title"),
            "status": payload.get("status"), "teacher_available": payload.get("teacher_available"),
            "teacher_model": payload.get("teacher_model"), "teacher_error": payload.get("teacher_error"),
            "score": exam.get("score"), "correct": exam.get("correct"), "total": exam.get("total"),
            "model_used": exam.get("model_used"), "cloud_used": exam.get("cloud_used"),
            "expected_withheld": exam.get("expected_withheld"),
            "stage_passed": payload.get("stage_passed"), "promoted": payload.get("promoted"),
            "next_stage": payload.get("next_stage"),
        })
    return rows


def _database_metrics(path: Path) -> tuple[dict[str, Any], str | None]:
    if not path.is_file():
        return {}, "native_lexical_database_missing"
    try:
        uri = f"file:{path}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout=10000")
            counts = {
                "lexemes": int(connection.execute("SELECT COUNT(*) FROM lexemes").fetchone()[0]),
                "verified_lexemes": int(connection.execute(
                    "SELECT COUNT(*) FROM lexemes WHERE verified=1").fetchone()[0]),
                "relations": int(connection.execute("SELECT COUNT(*) FROM relations").fetchone()[0]),
                "teacher_lessons": int(connection.execute(
                    "SELECT COUNT(*) FROM teacher_lessons").fetchone()[0]),
                "practice_attempts": int(connection.execute(
                    "SELECT COUNT(*) FROM practice_attempts").fetchone()[0]),
                "verified_correct_attempts": int(connection.execute(
                    "SELECT COUNT(*) FROM practice_attempts WHERE correct=1").fetchone()[0]),
            }
            tables = {str(row[0]) for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
            if "acquired_concepts" in tables:
                acquisition_rows = connection.execute(
                    "SELECT stage,COUNT(*) AS senses,COUNT(DISTINCT lemma) AS words "
                    "FROM acquired_concepts GROUP BY stage"
                ).fetchall()
                active_stages = (
                    "retention_1d", "retention_7d", "retention_30d",
                    "retention_90d", "mastered",
                )
                counts["encountered_words"] = int(connection.execute(
                    "SELECT COUNT(DISTINCT lemma) FROM acquired_concepts"
                ).fetchone()[0])
                counts["acquired_senses"] = int(connection.execute(
                    "SELECT COUNT(*) FROM acquired_concepts"
                ).fetchone()[0])
                counts["active_vocabulary"] = int(connection.execute(
                    "SELECT COUNT(DISTINCT lemma) FROM acquired_concepts "
                    "WHERE stage IN (?,?,?,?,?)", active_stages,
                ).fetchone()[0])
                counts["mastered_words"] = int(connection.execute(
                    "SELECT COUNT(DISTINCT lemma) FROM acquired_concepts WHERE stage='mastered'"
                ).fetchone()[0])
                counts["acquisition_stages"] = {
                    str(row["stage"]): {"senses": int(row["senses"]), "words": int(row["words"])}
                    for row in acquisition_rows
                }
            else:
                counts.update({"encountered_words": 0, "acquired_senses": 0,
                               "active_vocabulary": 0, "mastered_words": 0,
                               "acquisition_stages": {}})
            if "native_wordwall_attempts" in tables:
                counts["wordwall_attempts"] = int(connection.execute(
                    "SELECT COUNT(*) FROM native_wordwall_attempts"
                ).fetchone()[0])
                wordwall_correct = int(connection.execute(
                    "SELECT COUNT(*) FROM native_wordwall_attempts WHERE correct=1"
                ).fetchone()[0])
                counts["wordwall_accuracy"] = round(
                    wordwall_correct / counts["wordwall_attempts"], 4
                ) if counts["wordwall_attempts"] else None
            else:
                counts.update({"wordwall_attempts": 0, "wordwall_accuracy": None})
            columns = {
                str(row[1]) for row in connection.execute("PRAGMA table_info(practice_attempts)")
            }
            family_key = "curriculum_family" if "curriculum_family" in columns else "family"
            source_disjoint = "SUM(source_disjoint)" if "source_disjoint" in columns else "0"
            family_rows = connection.execute(
                f"""SELECT {family_key} AS family,COUNT(*) AS attempts,
                   COUNT(DISTINCT task_id) AS unique_tasks,SUM(correct) AS correct,
                   {source_disjoint} AS source_disjoint_attempts,
                   MIN(created_epoch) AS first_attempt_epoch,
                   MAX(created_epoch) AS last_attempt_epoch
                   FROM practice_attempts GROUP BY {family_key} ORDER BY {family_key}"""
            ).fetchall()
            journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
    except (OSError, sqlite3.Error) as exc:
        return {}, f"{type(exc).__name__}:{exc}"
    counts["practice_accuracy"] = round(
        counts["verified_correct_attempts"] / counts["practice_attempts"], 4
    ) if counts["practice_attempts"] else None
    counts["journal_mode"] = journal_mode
    counts["families"] = {
        str(row["family"]): {
            "attempts": int(row["attempts"]), "correct": int(row["correct"] or 0),
            "unique_tasks": int(row["unique_tasks"] or 0),
            "source_disjoint_attempts": int(row["source_disjoint_attempts"] or 0),
            "accuracy": round(int(row["correct"] or 0) / int(row["attempts"]), 4),
            "first_attempt_epoch": float(row["first_attempt_epoch"] or 0),
            "last_attempt_epoch": float(row["last_attempt_epoch"] or 0),
            "retention_span_seconds": max(
                0.0, float(row["last_attempt_epoch"] or 0)
                - float(row["first_attempt_epoch"] or 0)
            ),
        } for row in family_rows
    }
    return counts, None


def collect_native_english_progress(repo_root: Path | str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    now = time.time()
    state_path = root / "data/aion/native_english_teacher/state.json"
    cycles_path = root / "data/aion/native_english_teacher/cycles.jsonl"
    service_path = root / "results/aion_mastery_curriculum_service_status.json"
    competency_path = root / "backend/modules/hexcore/data/progressive_competency/state.json"
    state = _read_json(state_path)
    service_root = _read_json(service_path)
    service = service_root.get("native_english_teacher") or {}
    competency = _read_json(competency_path)
    english_subject = (competency.get("subjects") or {}).get("english") or {}
    try:
        english_assessment = ProgressiveCompetencySystem.assess_snapshot(
            repo_root=root, state=competency, subject_id="english",
        ) if english_subject else {}
    except (KeyError, TypeError, ValueError):
        english_assessment = {}
    database_path = default_database_path(root)
    database, database_error = _database_metrics(database_path)

    stage_index = min(max(0, int(state.get("stage_index") or 0)), len(CURRICULUM) - 1)
    stages = []
    for index, row in enumerate(CURRICULUM):
        family = str(row["family"])
        family_metrics = (database.get("families") or {}).get(family) or {}
        attempts = int(family_metrics.get("attempts") or 0)
        accuracy = family_metrics.get("accuracy")
        minimum = int(row["minimum_attempts"])
        threshold = float(row["pass_accuracy"])
        unique_tasks = int(family_metrics.get("unique_tasks") or 0)
        unique_ratio = round(unique_tasks / attempts, 4) if attempts else None
        qualified = bool(
            attempts >= minimum
            and unique_tasks >= minimum
            and float(accuracy or 0.0) >= threshold
            and float(unique_ratio or 0.0) >= float(row.get("minimum_unique_ratio") or 0.0)
        )
        if row.get("require_source_disjoint"):
            qualified = qualified and int(family_metrics.get("source_disjoint_attempts") or 0) >= minimum
        if row.get("minimum_retention_span_seconds"):
            qualified = qualified and float(
                family_metrics.get("retention_span_seconds") or 0.0
            ) >= float(row["minimum_retention_span_seconds"])
        stages.append({
            **dict(row), "number": index + 1,
            "track": str(row.get("track") or ("foundation" if index < 7 else "intermediate")),
            "implemented": bool(row.get("implemented", True)),
            "attempts": attempts, "correct": int(family_metrics.get("correct") or 0),
            "unique_tasks": unique_tasks,
            "repeat_attempts": max(0, attempts - unique_tasks),
            "unique_ratio": unique_ratio,
            "retention_span_seconds": float(
                family_metrics.get("retention_span_seconds") or 0.0
            ),
            "source_disjoint_attempts": int(family_metrics.get("source_disjoint_attempts") or 0),
            "accuracy": accuracy, "qualified_by_totals": qualified,
            "attempt_progress": min(1.0, attempts / minimum) if minimum else 1.0,
            "status": "completed" if (
                          index < stage_index
                          or (index == stage_index and bool(state.get("curriculum_complete")))
                      ) else
                      "current" if index == stage_index else "locked",
        })

    interval = float(service.get("interval_seconds") or 300.0)
    last_cycle_epoch = float(state.get("last_cycle_epoch") or 0.0)
    last_success_age = max(0.0, now - last_cycle_epoch) if last_cycle_epoch else None
    service_error = None
    if str(service.get("status") or "").lower() == "error":
        service_error = str(service.get("detail") or service.get("error") or "teacher_service_error")
    sd_mounted = database_path.is_file() and str(database_path).startswith("/Volumes/")
    volume_root = Path("/")
    if str(database_path).startswith("/Volumes/"):
        parts = database_path.parts
        volume_root = Path(*parts[:3]) if len(parts) >= 3 else Path("/Volumes")
    try:
        capacity = shutil.disk_usage(volume_root)
        storage = {
            "volume_root": str(volume_root), "total_bytes": capacity.total,
            "used_bytes": capacity.used, "free_bytes": capacity.free,
            "free_gib": round(capacity.free / 1024 ** 3, 2),
        }
    except OSError:
        storage = {"volume_root": str(volume_root), "free_gib": None}
    blockers: list[str] = []
    if database_error:
        blockers.append(database_error)
    if not sd_mounted:
        blockers.append("sd_native_english_store_not_mounted")
    if service_error:
        blockers.append(service_error)
    if last_success_age is None or last_success_age > interval * 2.5:
        blockers.append("no_recent_completed_teacher_cycle")
    current_stage = stages[stage_index]
    if not current_stage["implemented"]:
        blockers.append("native_exam_family_not_implemented")

    last_exam = dict(state.get("last_exam") or {})
    last_exam.pop("attempts", None)
    learning_active = bool(
        service.get("enabled", True) and not blockers
        and last_exam.get("model_used") is False
        and last_exam.get("expected_withheld") is True
    )
    health = "healthy" if learning_active else "degraded" if database_path.is_file() else "offline"
    return {
        "schema_version": "aion.native_english_progress.v2",
        "generated_epoch": now,
        "generated_at": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
        "health": health, "learning_active": learning_active, "blockers": blockers,
        "stage": {
            "current_index": stage_index, "current_number": stage_index + 1,
            "total": len(CURRICULUM), "id": current_stage["id"],
            "title": current_stage["title"],
            "consecutive_passes": min(2, int(state.get("consecutive_stage_passes") or 0)),
            "required_consecutive_passes": 2,
            "curriculum_complete": bool(state.get("curriculum_complete")),
            "progress": round(stage_index / max(1, len(CURRICULUM) - 1), 4),
        },
        "curriculum": stages,
        "teacher": {
            "cycles": int(state.get("cycles") or 0), "model": state.get("last_teacher_model"),
            "last_error": state.get("last_teacher_error"), "last_cycle_epoch": last_cycle_epoch or None,
            "last_success_age_seconds": last_success_age, "service": dict(service),
        },
        "exam": {"last": last_exam, "separation_verified": bool(
            last_exam.get("model_used") is False and last_exam.get("cloud_used") is False
            and last_exam.get("expected_withheld") is True
        )},
        "memory": {**database, "database_error": database_error},
        "storage": {
            **storage, "database_path": str(database_path), "database_exists": database_path.is_file(),
            "sd_mounted": sd_mounted, "readable": os.access(database_path, os.R_OK),
            "writable": os.access(database_path, os.W_OK),
        },
        "learning_centre": {
            "overall_level": english_assessment.get("overall_level", "unassessed"),
            "knowledge_level": english_assessment.get("knowledge_level", "unassessed"),
            "practical_level": english_assessment.get("practical_level", "unassessed"),
            "evidence_records": english_assessment.get("evidence_records", 0),
            "raw_evidence_records": english_assessment.get("raw_evidence_records", 0),
            "target_reached": english_assessment.get("target_reached", False),
            "coverage": english_assessment.get("coverage") or {},
            "open_blockers": english_assessment.get("open_blockers") or [],
            "subskills": english_subject.get("subskills") or [],
        },
        "recent_cycles": _recent_cycles(cycles_path),
        "paths": {
            "teacher_state": str(state_path), "cycle_ledger": str(cycles_path),
            "service_status": str(service_path), "competency_state": str(competency_path),
        },
        "claim_boundary": (
            "The imported reference lexicon is not learned vocabulary. "
            "Only concepts that pass closed-book production and delayed retention enter Aion's active vocabulary. "
            "Sentence and discourse advancement additionally requires unique, sealed, "
            "source-disjoint native examinations."
        ),
    }


__all__ = ["collect_native_english_progress"]
