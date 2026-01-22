# backend/modules/aion_demo/reflex_grid.py
"""
AION Reflex Demo (Cognitive Grid)
- Real: runs the grid agent, persists state to a JSON file, exposes step/run semantics.
- Safe: no hard dependency on optional AION subsystems (broadcast_event/process_event/apply_feedback).
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

# ------------------------ Constants ------------------------

GRID_SIZE = 10
OBJECTS = ["bed", "desk", "coffee", "window"]
DANGERS = ["pit", "spike"]
VISION_RANGE = 2

# bounded “proof of life”
STEP_INTERVAL_S_DEFAULT = 0.25       # runner cadence
EPISODE_STEPS_DEFAULT = 80           # ~20s at 0.25s/step
MAX_RUNTIME_S_DEFAULT = 300          # 5 minutes cap
MAX_EPISODES_DEFAULT = 5             # 5 episodes cap

SYMBOLS: Dict[str, Dict[str, Any]] = {
    "π": {"meaning": "pattern", "coherence": +0.12, "curiosity": +0.05},
    "μ": {"meaning": "measure", "clarity": +0.10, "focus": +0.04},
    "∇": {"meaning": "collapse", "reflection": +0.08, "entropy": -0.06},
    "⟲": {"meaning": "resonance", "stability": +0.15, "energy": +0.03},
    "↔": {"meaning": "entanglement", "connectivity": +0.09, "coherence": +0.05},
    "⊕": {"meaning": "superposition", "creativity": +0.07, "entropy": +0.03},
    "💡": {"meaning": "photon", "insight": +0.11, "clarity": +0.08},
    "🌊": {"meaning": "wave", "fluidity": +0.09, "adaptation": +0.05},
}
SYMBOL_DENSITY = 0.20


# ------------------------ Helpers ------------------------

def _normalize(v: float, lo: float, hi: float) -> float:
    if hi == lo:
        return 0.0
    return max(0.0, min(1.0, (v - lo) / (hi - lo)))


def _curiosity_score(tile: Tuple[int, int], visited: Dict[str, int]) -> float:
    k = f"{tile[0]},{tile[1]}"
    return 1.0 / (1.0 + float(visited.get(k, 0)))


def _spawn_world(rng: random.Random) -> Dict[str, str]:
    # store as {"x,y": "token"}
    all_tiles = [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE)]
    positions = rng.sample(all_tiles, len(OBJECTS) + len(DANGERS))
    world: Dict[str, str] = {}

    for i, obj in enumerate(OBJECTS + DANGERS):
        x, y = positions[i]
        world[f"{x},{y}"] = obj

    # sprinkle symbols
    for (x, y) in all_tiles:
        k = f"{x},{y}"
        if k in world:
            continue
        if rng.random() < SYMBOL_DENSITY:
            world[k] = rng.choice(list(SYMBOLS.keys()))
    return world


def _sense(world: Dict[str, str], pos: Tuple[int, int]) -> Dict[str, str]:
    x, y = pos
    visible: Dict[str, str] = {}
    for dx in range(-VISION_RANGE, VISION_RANGE + 1):
        for dy in range(-VISION_RANGE, VISION_RANGE + 1):
            nx, ny = x + dx, y + dy
            if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
                k = f"{nx},{ny}"
                obj = world.get(k)
                if obj:
                    visible[k] = obj
    return visible


def _choose_move(rng: random.Random, pos: Tuple[int, int], visited: Dict[str, int]) -> str:
    x, y = pos
    dirs = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}

    best: List[Tuple[str, float]] = []
    best_score = -1.0
    for d, (dx, dy) in dirs.items():
        nx = max(0, min(GRID_SIZE - 1, x + dx))
        ny = max(0, min(GRID_SIZE - 1, y + dy))
        s = _curiosity_score((nx, ny), visited)
        if s > best_score:
            best_score = s
            best = [(d, s)]
        elif abs(s - best_score) < 1e-12:
            best.append((d, s))

    return rng.choice(best)[0] if best else rng.choice(list(dirs.keys()))


def _apply_optional_feedback(kind: str) -> None:
    # best-effort: never break demo if these modules aren’t available
    try:
        from backend.modules.aion_resonance.cognitive_feedback import apply_feedback
        apply_feedback(kind)
    except Exception:
        return


async def _optional_broadcast(event: Dict[str, Any]) -> None:
    try:
        from backend.modules.aion_resonance.thought_stream import broadcast_event
        await broadcast_event(event)
    except Exception:
        return


async def _optional_symbolic_map(event_type: str, phi_state: Dict[str, Any], belief_state: Dict[str, Any]) -> None:
    try:
        from backend.modules.aion_resonance.aion_symbolic_mapper import process_event
        await process_event(event_type=event_type, phi_state=phi_state, belief_state=belief_state)
    except Exception:
        return


@dataclass
class RunController:
    lock: asyncio.Lock
    task: Optional[asyncio.Task]


_CTRL = RunController(lock=asyncio.Lock(), task=None)


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


# ------------------------ State init / reset ------------------------

def _init_state(seed: int) -> Dict[str, Any]:
    rng = random.Random(seed)
    world = _spawn_world(rng)

    now = time.time()
    state: Dict[str, Any] = {
        "ok": True,
        "seed": seed,

        "grid_size": GRID_SIZE,
        "vision_range": VISION_RANGE,

        # episode config
        "episode_max_steps": EPISODE_STEPS_DEFAULT,

        # run budget (bounded; protects wallet)
        "run_active": False,
        "run_id": None,
        "run_started_at": None,
        "run_budget_s": MAX_RUNTIME_S_DEFAULT,
        "run_budget_episodes": MAX_EPISODES_DEFAULT,

        # counters
        "episode_id": 1,
        "episodes_completed": 0,
        "lifetime_score": 0,
        "episode_score": 0,

        "now_s": now,
        "timestamp": now,

        "position": {"x": 0, "y": 0},
        "visited": {"0,0": 1},
        "collected": [],
        "alive": True,
        "steps": 0,

        # back-compat with existing UIs (some show "score")
        "score": 0,

        "last_outcome": "Initialized",
        "last_reflection": "Curiosity engaged.",
        "last_event_type": "init",
        "last_tile": "0,0",
        "stability_breached": False,

        "metrics": {"novelty": 1.0, "coherence": 1.0, "entropy": 0.0},

        "world": world,  # {"x,y": token}
        "events": [],    # last ~32 reflections
    }
    return state


def _reset_episode_inplace(st: Dict[str, Any], seed: int) -> None:
    rng = random.Random(seed)
    st["seed"] = seed
    st["world"] = _spawn_world(rng)

    st["position"] = {"x": 0, "y": 0}
    st["visited"] = {"0,0": 1}
    st["collected"] = []
    st["alive"] = True
    st["steps"] = 0

    st["episode_score"] = 0.0
    st["score"] = 0.0
    st["stability_breached"] = False
    st["last_tile"] = "0,0"
    st["last_event_type"] = "episode_reset"
    st["last_outcome"] = "Episode reset"
    st["last_reflection"] = "Episode reset."
    st["metrics"] = {"novelty": 1.0, "coherence": 1.0, "entropy": 0.0}

    st["events"] = (st.get("events", []) or [])[-24:]
    st["timestamp"] = time.time()


def reset(path: Path, seed: Optional[int] = None) -> Dict[str, Any]:
    seed = int(seed if seed is not None else int(time.time() * 1000) % 2_000_000_000)
    st = _init_state(seed)
    _write_json(path, st)
    return st


def get_state(path: Path) -> Dict[str, Any]:
    st = _read_json(path, default=None)
    if not isinstance(st, dict):
        st = reset(path)

    now_s = time.time()
    ts = float(st.get("timestamp", 0.0) or 0.0)
    st["now_s"] = now_s
    st["age_ms"] = int(max(0.0, (now_s - ts) * 1000.0))

    # expose run budget remaining (best-effort)
    if st.get("run_active"):
        started = float(st.get("run_started_at") or now_s)
        budget_s = float(st.get("run_budget_s") or MAX_RUNTIME_S_DEFAULT)
        budget_eps = int(st.get("run_budget_episodes") or MAX_EPISODES_DEFAULT)
        eps_done = int(st.get("episodes_completed") or 0)

        st["run_time_left_s"] = max(0.0, budget_s - (now_s - started))
        st["run_episodes_left"] = max(0, budget_eps - eps_done)
    else:
        st["run_time_left_s"] = 0.0
        st["run_episodes_left"] = 0

    return st


# ------------------------ Core step ------------------------

def _step_core(st: Dict[str, Any]) -> Dict[str, Any]:
    now = time.time()
    st["now_s"] = now

    # compute run remaining (if active) + enforce hard stop
    if st.get("run_active"):
        started = float(st.get("run_started_at") or now)
        budget_s = float(st.get("run_budget_s") or MAX_RUNTIME_S_DEFAULT)
        budget_eps = int(st.get("run_budget_episodes") or MAX_EPISODES_DEFAULT)
        eps_done = int(st.get("episodes_completed") or 0)

        time_left = max(0.0, budget_s - (now - started))
        eps_left = max(0, budget_eps - eps_done)
        st["run_time_left_s"] = time_left
        st["run_episodes_left"] = eps_left

        if time_left <= 0.0 or eps_left <= 0:
            st["run_active"] = False
            st["last_event_type"] = "run_complete"
            st["last_outcome"] = "Run budget exhausted"
            st["last_reflection"] = "Run complete (budget exhausted)."
            st["timestamp"] = now
            return st

    # episode termination check (dead OR max steps)
    steps = int(st.get("steps", 0) or 0)
    ep_max = int(st.get("episode_max_steps", EPISODE_STEPS_DEFAULT) or EPISODE_STEPS_DEFAULT)

    if (not st.get("alive", True)) or (steps >= ep_max):
        st["episodes_completed"] = int(st.get("episodes_completed", 0) or 0) + 1
        st["lifetime_score"] = float(st.get("lifetime_score", 0) or 0) + float(st.get("episode_score", 0) or 0)

        reason = "death" if not st.get("alive", True) else "timeout"
        st["last_event_type"] = "episode_end"
        st["last_outcome"] = f"Episode ended ({reason})"
        st["last_reflection"] = f"Episode ended ({reason}). Resetting…"

        events = st.get("events", []) or []
        events.append(
            {
                "ts": now,
                "type": "episode_end",
                "reason": reason,
                "episode_id": int(st.get("episode_id", 1) or 1),
                "score": float(st.get("episode_score", 0) or 0),
            }
        )
        st["events"] = events[-32:]
        st["timestamp"] = now

        # auto-reset only if run is active and budget remains
        if st.get("run_active"):
            started = float(st.get("run_started_at") or now)
            budget_s = float(st.get("run_budget_s") or MAX_RUNTIME_S_DEFAULT)
            budget_eps = int(st.get("run_budget_episodes") or MAX_EPISODES_DEFAULT)
            eps_done = int(st.get("episodes_completed") or 0)

            if (now - started) < budget_s and eps_done < budget_eps:
                st["episode_id"] = int(st.get("episode_id", 1) or 1) + 1
                new_seed = int(now * 1000) % 2_000_000_000
                _reset_episode_inplace(st, new_seed)
            else:
                st["run_active"] = False
                st["last_event_type"] = "run_complete"
                st["last_outcome"] = "Run complete"
                st["last_reflection"] = "Run complete."
                st["timestamp"] = now

        return st

    # normal step
    seed = int(st.get("seed", 0) or 0)
    rng = random.Random(seed + steps * 1009)

    x = int(st.get("position", {}).get("x", 0))
    y = int(st.get("position", {}).get("y", 0))
    visited: Dict[str, int] = st.get("visited", {}) or {}
    world: Dict[str, str] = st.get("world", {}) or {}

    direction = _choose_move(rng, (x, y), visited)
    dx, dy = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}[direction]
    nx = max(0, min(GRID_SIZE - 1, x + dx))
    ny = max(0, min(GRID_SIZE - 1, y + dy))
    tile = f"{nx},{ny}"

    st["position"] = {"x": nx, "y": ny}
    visited[tile] = int(visited.get(tile, 0) or 0) + 1
    st["visited"] = visited
    st["steps"] = steps + 1
    st["last_tile"] = tile

    obj = world.get(tile)

    # Metrics
    vision = _sense(world, (nx, ny))
    novelty = _curiosity_score((nx, ny), visited)
    coherence = 1.0 - _normalize(float(len(vision)), 0.0, 25.0)
    entropy = _normalize(rng.random(), 0.0, 1.0)

    event_type = "move"
    outcome = f"➡️ moved {direction} to {tile}"

    # scoring (simple + stable)
    step_penalty = -0.01
    reward_delta = step_penalty

    if obj in DANGERS:
        st["alive"] = False
        st["stability_breached"] = True
        entropy = 1.0
        coherence = max(0.0, coherence - 0.35)
        outcome = f"💀 stepped on {obj}"
        event_type = "danger"
        reward_delta += -2.0
        _apply_optional_feedback("danger")

    elif obj in OBJECTS:
        collected = set(st.get("collected", []) or [])
        if obj not in collected:
            collected.add(obj)
            st["collected"] = sorted(collected)
            outcome = f"✅ collected {obj}"
            event_type = "collect"
            reward_delta += +1.0
            _apply_optional_feedback("collect")

    elif obj in SYMBOLS:
        sym = SYMBOLS[obj]
        coherence += float(sym.get("coherence", 0.0) or 0.0)
        entropy += float(sym.get("entropy", 0.0) or 0.0)
        novelty += float(sym.get("curiosity", 0.0) or 0.0)
        coherence = max(0.0, min(1.2, coherence))
        entropy = max(0.0, min(1.2, entropy))
        novelty = max(0.0, min(1.2, novelty))
        outcome = f"🔣 encountered symbol {obj} ({sym.get('meaning','?')})"
        event_type = "symbol"
        reward_delta += +0.05
        _apply_optional_feedback("symbol")
    else:
        _apply_optional_feedback("move")

    st["episode_score"] = float(st.get("episode_score", 0) or 0) + float(reward_delta)
    st["score"] = st["episode_score"]  # back-compat

    if event_type == "danger":
        reflection = (
            f"Curiosity={novelty:.2f}, Coherence={coherence:.2f}, Entropy={entropy:.2f}. "
            f"Stability breached. {outcome}"
        )
    else:
        reflection = f"Curiosity={novelty:.2f}, Coherence={coherence:.2f}, Entropy={entropy:.2f}. {outcome}"

    st["metrics"] = {
        "novelty": float(novelty),
        "coherence": float(coherence),
        "entropy": float(entropy),
    }
    st["last_outcome"] = outcome
    st["last_reflection"] = reflection
    st["last_event_type"] = event_type
    st["timestamp"] = now

    events = st.get("events", []) or []
    events.append(
        {
            "ts": now,
            "type": event_type,
            "tile": tile,
            "token": obj,
            "reflection": reflection,
        }
    )
    st["events"] = events[-32:]

    return st


# ------------------------ Public API ------------------------

async def step_once(path: Path) -> Dict[str, Any]:
    st = get_state(path)
    st = _step_core(st)

    # optional integrations (best-effort)
    event = {
        "type": "self_reflection",
        "tone": "curious" if st.get("last_event_type") != "danger" else "alarm",
        "message": st.get("last_reflection"),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(st.get("timestamp", time.time())))),
    }
    await _optional_broadcast(event)

    et = st.get("last_event_type") or "move"
    await _optional_symbolic_map(
        event_type=et,
        phi_state={
            "Φ_coherence": float(st["metrics"]["coherence"]),
            "Φ_entropy": float(st["metrics"]["entropy"]),
            "Φ_flux": 0.0,
            "Φ_load": 0.0,
        },
        belief_state={
            "curiosity": float(st["metrics"]["novelty"]),
            "stability": 0.5 if et != "danger" else 0.0,
        },
    )

    _write_json(path, st)
    return st


async def start_run(
    path: Path,
    interval_s: float = STEP_INTERVAL_S_DEFAULT,
    max_runtime_s: int = MAX_RUNTIME_S_DEFAULT,
    max_episodes: int = MAX_EPISODES_DEFAULT,
    episode_steps: int = EPISODE_STEPS_DEFAULT,
) -> Dict[str, Any]:
    async with _CTRL.lock:
        # if already running, return current state
        if _CTRL.task is not None and not _CTRL.task.done():
            return get_state(path)

        st = get_state(path)
        now = time.time()

        st["run_active"] = True
        st["run_id"] = int(now * 1000)
        st["run_started_at"] = now
        st["run_budget_s"] = int(max_runtime_s)
        st["run_budget_episodes"] = int(max_episodes)
        st["episode_max_steps"] = int(max(1, episode_steps))
        st["timestamp"] = now

        _write_json(path, st)

        async def _runner():
            while True:
                st2 = get_state(path)
                if not st2.get("run_active"):
                    break
                await step_once(path)
                await asyncio.sleep(float(interval_s))

        _CTRL.task = asyncio.create_task(_runner())
        return get_state(path)