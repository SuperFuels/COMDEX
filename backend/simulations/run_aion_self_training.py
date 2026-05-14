#!/usr/bin/env python3
"""
🧠 AION Self-Training Loop - Phase 47B + 48A/48B
─────────────────────────────────────────────────
Closed-loop harmonic reinforcement cycle with:
  * Phase 47A  : aion_self_trainer (reinforcement)
  * Phase 22   : cee_autotester (evaluation)
  * Phase 48A  : Advanced Lexical Cognition (task gen+run+report)
  * Phase 48B  : Semantic Comprehension Benchmark (MCI)
  * Harmonic feedback + adaptive decay
  * Live dashboard sync

Outputs:
  data/analysis/aion_selftrain_cycle<N>.json
  data/analysis/aion_selftrain_summary.json
"""

import argparse, json, time, logging
from pathlib import Path
from statistics import mean

from backend.modules.aion_cognition import aion_self_trainer, cee_autotester
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_language.harmonic_memory_profile import HarmonicMemoryProfile

# Optional dashboard hook (safe if absent)
try:
    from backend.simulations.run_aion_cognitive_bridge import update_bridge_dashboard
except Exception:
    update_bridge_dashboard = lambda _: None

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

RMC = ResonantMemoryCache()
HMP = HarmonicMemoryProfile()

REPORT_DIR = Path("data/analysis")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def run_training_cycle(
    cycle: int,
    limit: int = 400,
    lce_enabled: bool = True,
    lce_size: int = 150,
    bench_enabled: bool = True,
    bench_size: int = 100,
):
    """Run one full harmonic + cognition + benchmark cycle."""
    log.info(f"\n🌀 Starting harmonic cycle {cycle} (limit={limit})")

    # Phase 47A - Self-training reinforcement
    self_summary = aion_self_trainer.run_self_training(limit=limit)
    log.info(f"[Cycle {cycle}] Self-training completed -> {self_summary.get('successful', 0)} reinforced")

    # Phase 22 - Evaluation pass
    metrics = cee_autotester.run_autotest(sample_size=150)
    log.info(f"[Cycle {cycle}] Autotest summary: {metrics}")

    # Phase 48A - Advanced Cognition Layer (task gen -> run -> report)
    cognition_summary = {"active": False}
    if lce_enabled:
        try:
            log.info(f"[Cycle {cycle}] 🔥 Entering LCE (Advanced Cognition) - size={lce_size}")
            from backend.modules.aion_cognition.advanced_cognition import (
                lexical_task_generator, lexical_task_runner, lexical_task_reporter
            )

            gen_info = lexical_task_generator.generate_tasks(cycle=cycle, limit=lce_size)
            log.info(f"[Cycle {cycle}] 🧩 LCE task generation completed -> {gen_info}")

            task_path = Path(gen_info["path"])
            cognition_summary = lexical_task_runner.run_taskset(task_path)
            lexical_task_reporter.log_cycle(cycle, cognition_summary)

            log.info(
                f"[Cycle {cycle}] 🧠 Advanced Cognition completed -> "
                f"acc={cognition_summary.get('avg_accuracy', 0.0):.3f}, "
                f"SQI={cognition_summary.get('avg_SQI', 0.0):.3f}"
            )
        except Exception as e:
            log.warning(f"[Cycle {cycle}] ⚠ Advanced Cognition skipped: {e}")
            cognition_summary = {"active": False, "error": str(e)}

    # Phase 48B - Semantic Comprehension Benchmark (MCI)
    benchmark_summary = {"active": False}
    if bench_enabled:
        try:
            from backend.modules.aion_cognition.semantic_benchmark import (
                benchmark_task_generator, benchmark_runner, benchmark_reporter
            )
            gen_info = benchmark_task_generator.generate_tasks(sample_size=bench_size, cycle=cycle)
            bench_path = Path(gen_info["path"])
            benchmark_summary = benchmark_runner.run_taskset(bench_path)
            benchmark_reporter.log_cycle(cycle, benchmark_summary)
            log.info(
                f"[Cycle {cycle}] 📘 Semantic Benchmark -> "
                f"MCI={benchmark_summary.get('avg_MCI', 0.0):.3f}, "
                f"sim={benchmark_summary.get('avg_similarity', 0.0):.3f}"
            )
        except Exception as e:
            log.warning(f"[Cycle {cycle}] ⚠ Semantic Benchmark skipped: {e}")
            benchmark_summary = {"active": False, "error": str(e)}

    # Harmonic feedback loop
    avg_sqi = metrics.get("avg_SQI", 0.5)
    avg_stab = metrics.get("avg_stability", 0.5)
    decay_rate = round(max(0.0005, 0.002 * (1 - avg_stab)), 6)

    RMC.stabilize(decay_rate=decay_rate)
    HMP.log_event({
        "cycle": cycle,
        "avg_SQI": avg_sqi,
        "avg_stability": avg_stab,
        "decay_rate": decay_rate,
        "timestamp": time.time(),
    })

    # Snapshot save
    snapshot = {
        "cycle": cycle,
        "avg_SQI": avg_sqi,
        "avg_stability": avg_stab,
        "decay_rate": decay_rate,
        "self_summary": self_summary,
        "metrics": metrics,
        "advanced_cognition": cognition_summary,
        "semantic_benchmark": benchmark_summary,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    out = REPORT_DIR / f"aion_selftrain_cycle{cycle}.json"
    out.write_text(json.dumps(snapshot, indent=2))
    log.info(f"[Cycle {cycle}] ✅ Snapshot saved -> {out}")

    # Live dashboard
    update_bridge_dashboard(snapshot)

    return snapshot


def run_closed_loop(
    total_cycles: int = 3,
    limit: int = 400,
    lce_enabled: bool = True,
    lce_size: int = 150,
    bench_enabled: bool = True,
    bench_size: int = 100,
):
    """Main orchestrator loop with adaptive feedback."""
    sqi_values = []

    for c in range(1, total_cycles + 1):
        snap = run_training_cycle(
            cycle=c,
            limit=limit,
            lce_enabled=lce_enabled,
            lce_size=lce_size,
            bench_enabled=bench_enabled,
            bench_size=bench_size,
        )
        sqi_values.append(snap["avg_SQI"])
        avg_sqi = round(mean(sqi_values), 3)
        log.info(f"[Loop] 🔁 Completed {c}/{total_cycles} cycles (avg SQI={avg_sqi})")

    summary = {
        "total_cycles": total_cycles,
        "avg_SQI": round(mean(sqi_values), 3) if sqi_values else 0.0,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (REPORT_DIR / "aion_selftrain_summary.json").write_text(json.dumps(summary, indent=2))
    log.info("✅ Harmonic self-training loop finished.")
    return summary


def parse_args():
    p = argparse.ArgumentParser(description="AION Self-Training (47B + 48A/48B)")
    p.add_argument("--cycles", type=int, default=3, help="Total cycles to run")
    p.add_argument("--limit",  type=int, default=400, help="Max items reinforced in 47A")
    p.add_argument("--no-lce", action="store_true", help="Disable Lexical Cognition Evaluator")
    p.add_argument("--lce-size", type=int, default=150, help="Tasks generated per cycle (LCE)")
    p.add_argument("--no-bench", action="store_true", help="Disable Semantic Benchmark (MCI)")
    p.add_argument("--bench-size", type=int, default=100, help="Benchmark tasks per cycle")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    log.info("🔗 AION Harmonic Self-Training Loop - Phase 47B/48A/48B (Adaptive)")
    summary = run_closed_loop(
        total_cycles=args.cycles,
        limit=args.limit,
        lce_enabled=not args.no_lce,
        lce_size=args.lce_size,
        bench_enabled=not args.no_bench,
        bench_size=args.bench_size,
    )
    print(json.dumps(summary, indent=2))

import matplotlib.pyplot as plt
import json, glob

# Gather all cycle files
paths = sorted(glob.glob("data/analysis/aion_selftrain_cycle*.json"))
sqis = []
cycles = []

for p in paths:
    with open(p) as f:
        data = json.load(f)
        cycles.append(len(cycles) + 1)
        sqis.append(data.get("SQI") or data.get("sqi") or 0)

plt.figure(figsize=(6,4))
plt.plot(cycles, sqis, marker='o')
plt.title("AION Self-Training SQI Progress")
plt.xlabel("Cycle")
plt.ylabel("Symatic Quality Index (SQI)")
plt.grid(True)
plt.tight_layout()
plt.savefig("data/analysis/aion_sqi_progress.png")
print("📈 SQI progress plot saved -> data/analysis/aion_sqi_progress.png")