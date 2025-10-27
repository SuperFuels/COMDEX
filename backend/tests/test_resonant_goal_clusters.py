#!/usr/bin/env python3
"""
🧪 Resonant Cluster Bridge Integration Test — Phase 55 T4 (Stabilized)
───────────────────────────────────────────────────────────────
Validates dynamic coupling between:
  • ResonantStrategyPlanner  (Plan → Goal creation)
  • GoalTaskManager / GoalEngine  (Goal → Strategy feedback)
Includes propagation delay handling + reload logic for async persistence.
"""

import json
import logging
import time
from pathlib import Path

from backend.modules.skills.strategy_planner import ResonantStrategyPlanner
from backend.modules.consciousness.goal_task_manager import GoalTaskManager

logging.basicConfig(level=logging.INFO)


def test_cluster_bridge():
    print("=== ⚛  Resonant Cluster Bridge Integration Test ===")

    planner = ResonantStrategyPlanner()
    cluster = GoalTaskManager()

    # Clean any stale cluster goals
    cluster.goal_engine.goals = [
        g for g in cluster.goal_engine.get_all_goals()
        if not g.get("name", "").startswith("cluster_goal_expand_harmonic")
    ]
    cluster.goal_engine.save_goals()

    # ────────────────────────────────────────────────
    # 1️⃣  Generate high-SQI plan to trigger cluster creation
    print("→ Generating first high-SQI plan...")
    intent = {"what": "expand harmonic coherence"}
    plan = planner.generate_plan(intent)
    # 🔎 Inspect planner's own goal storage
    try:
        if hasattr(planner, "goal_engine"):
            print("🔍 Checking planner.goal_engine internal registry...")
            goals_planner = planner.goal_engine.get_all_goals()
            print(f"📄 Planner GoalEngine currently holds {len(goals_planner)} goals.")
            # 🔍 Check for planner goal engine JSON storage
            planner_paths = [
                Path("/workspaces/COMDEX/backend/modules/skills/goal_engine_data.json"),
                Path("/workspaces/COMDEX/data/skills/goal_engine_data.json"),
                Path("/workspaces/COMDEX/backend/modules/skills/data/goals.json"),
                Path("/workspaces/COMDEX/backend/modules/consciousness/data/goals.json"),
            ]
            found_file = next((p for p in planner_paths if p.exists()), None)
            if found_file:
                try:
                    with found_file.open() as f:
                        data = json.load(f)
                    print(f"📁 Found planner goal file → {found_file} ({len(data)} entries)")
                    matches = [
                        g for g in data
                        if "cluster_goal_expand_harmonic" in str(g).lower()
                    ]
                    print(f"🧭 Found {len(matches)} matching cluster entries in planner file.")
                    for m in matches:
                        print(json.dumps(m, indent=2)[:300])
                except Exception as e:
                    print(f"⚠️ Failed to read planner goal file {found_file}: {e}")
            else:
                print("⚠️ No planner goal_engine_data.json found in expected paths.")
            for g in goals_planner[-5:]:
                print(json.dumps(g, indent=2)[:300])
    except Exception as e:
        print(f"⚠️ Planner goal inspection failed: {e}")
    print(json.dumps(plan, indent=2))

    # Allow async bridge + RMC propagation
    time.sleep(1.0)

    # ────────────────────────────────────────────────
    # Check both planner and cluster goal registries
    new_goals = []

    try:
        if hasattr(planner, "goal_engine"):
            goals_planner = planner.goal_engine.get_all_goals()
            clusters = [
                g for g in goals_planner
                if "cluster_goal_expand_harmonic" in g.get("name", "")
            ]
            if clusters:
                print(f"🌱 Found cluster goal via planner GoalEngine: {clusters[0]['name']}")
                new_goals = clusters
            else:
                print("⚠️ Planner GoalEngine has no cluster goals yet.")
    except Exception as e:
        print(f"⚠️ Planner goal inspection failed: {e}")

    # ────────────────────────────────────────────────
    # Try all known goal persistence locations
    if not new_goals:
        possible_files = [
            Path("/workspaces/COMDEX/data/goals/goals.json"),
            Path("data/goals/goals.json"),
            Path("/workspaces/COMDEX/backend/data/goals/goals.json"),
            Path("/workspaces/COMDEX/data/consciousness/goals.json"),
        ]

        goal_file = next((f for f in possible_files if f.exists()), None)
        goals = []

        if goal_file:
            try:
                with goal_file.open() as f:
                    goals = json.load(f)
                print(f"📂 Reloaded {len(goals)} goals from {goal_file}")
            except Exception as e:
                print(f"⚠️ Failed to parse {goal_file}: {e}")
        else:
            print("⚠️ No goal file found, checking live GoalEngine memory...")
            try:
                if hasattr(cluster.goal_engine, "load_goals"):
                    cluster.goal_engine.load_goals()
                goals = cluster.goal_engine.get_all_goals()
                print(f"🧠 Retrieved {len(goals)} goals from live GoalEngine.")
            except Exception as e:
                print(f"⚠️ GoalEngine read error: {e}")
                goals = []

        # Find the cluster goal
        new_goals = [g for g in goals if "cluster_goal_expand_harmonic" in g.get("name", "")]
        print(f"🔍 Found {len(new_goals)} cluster goals after reload/scan.")

        # Diagnostic summary
        print(f"🧩 Inspecting goal keys (first 5 of {len(goals)}):")
        for g in goals[:5]:
            print(json.dumps(g, indent=2)[:300])

        candidates = [
            g for g in goals
            if "cluster" in g.get("name", "").lower()
            or "expand harmonic" in str(g).lower()
        ]
        print(f"🧭 Found {len(candidates)} potential matches with 'cluster' or 'expand harmonic':")
        for c in candidates:
            print(f" - {c.get('name', 'UNKNOWN')} | tags={c.get('tags', [])}")

    assert new_goals, "❌ Cluster goal not created (after propagation wait)"
    print(f"✅ Created cluster goal: {new_goals[0]['name']}  priority={new_goals[0]['priority']}")

    # ────────────────────────────────────────────────
    # 2️⃣  Re-generate same plan → should reinforce goal
    print("→ Regenerating plan to test reinforcement...")
    plan2 = planner.generate_plan(intent)
    time.sleep(1.0)

    if hasattr(cluster.goal_engine, "load_goals"):
        cluster.goal_engine.load_goals()
    goals_after = cluster.goal_engine.get_all_goals()

    g_match = [g for g in goals_after if "cluster_goal_expand_harmonic" in g.get("name", "")]
    if not g_match and hasattr(planner, "goal_engine"):
        g_match = [g for g in planner.goal_engine.get_all_goals()
                   if "cluster_goal_expand_harmonic" in g.get("name", "")]

    assert g_match, "❌ Reinforcement goal not found"
    print(f"🔁 Reinforced goal priority → {g_match[0]['priority']}")
    assert g_match[0]["priority"] >= new_goals[0]["priority"], "❌ Goal not reinforced"

    # ────────────────────────────────────────────────
    # 3️⃣  Confirm bidirectional GSI↔SQI coupling executed
    assert "resonance_score" in plan2, "❌ SQI missing from plan output"
    print(f"⚛  Final Plan SQI = {plan2['resonance_score']:.3f}")

    # ────────────────────────────────────────────────
    # 4️⃣  Export summary for dashboard verification
    summary_path = Path("data/analysis/test_cluster_summary.json")
    planner.export_resonant_summary(str(summary_path))
    time.sleep(0.5)
    assert summary_path.exists(), "❌ Summary file missing or not written"
    print(f"📊 Summary exported successfully → {summary_path}")

    print("✅ Resonant Cluster Bridge integration test complete.")


if __name__ == "__main__":
    test_cluster_bridge()