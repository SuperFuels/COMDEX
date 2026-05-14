# backend/api/ws.py
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.modules.consciousness.state_manager import StateManager

router = APIRouter()

clients: list[WebSocket] = []
QFC_CLIENTS: Set[WebSocket] = set()


async def _ws_send(ws: WebSocket, payload: Dict[str, Any]) -> None:
    try:
        await ws.send_text(json.dumps(payload, default=str))
    except Exception:
        pass

# ---- QFC broadcast helper (feeds /api/ws/qfc clients) ----
async def broadcast_to_qfc_clients(message: dict) -> None:
    dead = []
    for ws in list(QFC_CLIENTS):
        try:
            await _ws_send(ws, message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        try:
            QFC_CLIENTS.discard(ws)
        except Exception:
            pass


def fire_and_forget_qfc(message: dict) -> None:
    """Safe non-blocking emit (works even if called from sync code)."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcast_to_qfc_clients(message))
    except RuntimeError:
        asyncio.run(broadcast_to_qfc_clients(message))


async def broadcast_qfc(payload: Dict[str, Any]) -> None:
    if not QFC_CLIENTS:
        return
    msg = json.dumps(payload, default=str)
    dead: list[WebSocket] = []
    for ws in list(QFC_CLIENTS):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        QFC_CLIENTS.discard(ws)


def broadcast_qfc_sync(payload: Dict[str, Any]) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(broadcast_qfc(payload))


# containers WS (alias both)
@router.websocket("/api/ws/containers")
@router.websocket("/ws/containers")
async def container_ws(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            state = StateManager()
            containers = state.list_containers_with_status()
            await websocket.send_text(json.dumps({"containers": containers}, default=str))
            await asyncio.sleep(10)
    except Exception:
        pass
    finally:
        try:
            clients.remove(websocket)
        except ValueError:
            pass


def _lean_env() -> dict[str, str]:
    """
    Keep caches off the repo disk. Toolchain can be in ~/.elan (persist) or /tmp/.elan (ephemeral).
    """
    env = os.environ.copy()

    # If user has persistent elan installed, prefer it automatically.
    # Otherwise fallback to /tmp/.elan (older behavior).
    home_elan = os.path.expanduser("~/.elan")
    if os.path.exists(os.path.join(home_elan, "bin", "elan")):
        env["ELAN_HOME"] = home_elan
    else:
        env.setdefault("ELAN_HOME", "/tmp/.elan")

    env.setdefault("LAKE_HOME", "/tmp/.lake")
    env.setdefault("XDG_CACHE_HOME", "/tmp/.cache")
    env.setdefault("TMPDIR", "/tmp")

    # Ensure subprocess sees elan/lake/lean
    env["PATH"] = f"{env['ELAN_HOME']}/bin:" + env.get("PATH", "")
    return env


def _verify_snapshot_sync(
    *,
    steps: int,
    dt_ms: int,
    spec_version: str,
    scenario: str,
    kappa: float,
    chi: float,
    sigma: float,
    alpha: float,
) -> Dict[str, Any]:
    """
    Run the Lean snapshot verifier with full proof-identity inputs.
    Tries in-process import first; falls back to subprocess for robustness.
    """
    try:
        from backend.modules.lean.snapshot_verify import verify_snapshot  # type: ignore

        return verify_snapshot(
            steps=steps,
            dt_ms=dt_ms,
            spec_version=spec_version,
            scenario=scenario,
            kappa=kappa,
            chi=chi,
            sigma=sigma,
            alpha=alpha,
        )
    except Exception as e:
        cmd = [
            "python",
            "backend/modules/lean/snapshot_verify.py",
            "--steps",
            str(steps),
            "--dt-ms",
            str(dt_ms),
            "--spec-version",
            str(spec_version),
            "--scenario",
            str(scenario),
            "--kappa",
            str(kappa),
            "--chi",
            str(chi),
            "--sigma",
            str(sigma),
            "--alpha",
            str(alpha),
            "--json",
        ]
        proc = subprocess.run(
            cmd,
            cwd="/workspaces/COMDEX",
            capture_output=True,
            text=True,
            env=_lean_env(),
        )

        if proc.returncode != 0:
            return {
                "ok": False,
                "returncode": proc.returncode,
                "error": f"snapshot_verify subprocess failed: {type(e).__name__}: {e}",
                "stderr_tail": (proc.stderr or "").splitlines()[-40:],
                "stdout_tail": (proc.stdout or "").splitlines()[-40:],
            }

        try:
            return json.loads((proc.stdout or "").strip())
        except Exception:
            return {
                "ok": False,
                "returncode": proc.returncode,
                "error": "failed to parse JSON from snapshot_verify.py",
                "stderr_tail": (proc.stderr or "").splitlines()[-40:],
                "stdout_tail": (proc.stdout or "").splitlines()[-40:],
            }


def _safe_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _safe_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _safe_str(v: Any, default: str) -> str:
    try:
        s = str(v)
        return s if s else default
    except Exception:
        return default


# QFC WS (alias both)
@router.websocket("/api/ws/qfc")
@router.websocket("/ws/qfc")
async def qfc_ws(websocket: WebSocket):
    await websocket.accept()
    QFC_CLIENTS.add(websocket)
    await _ws_send(websocket, {"type": "qfc_ws_ready", "ts": int(time.time() * 1000)})

    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=15.0)
            except asyncio.TimeoutError:
                await _ws_send(websocket, {"type": "ping", "ts": int(time.time() * 1000)})
                continue

            try:
                data: Any = json.loads(msg)
            except Exception:
                continue

            if not isinstance(data, dict):
                continue

            if (data.get("type") or "").strip() != "snapshot_verify":
                continue

            # Required proof identity inputs
            steps = _safe_int(data.get("steps"), 1024)
            dt_ms = _safe_int(data.get("dt_ms"), 16)
            spec_version = _safe_str(data.get("spec_version"), "v1")

            # Scenario + slider knobs (these were missing before)
            scenario = _safe_str(data.get("scenario"), "BG01")
            kappa = _safe_float(data.get("kappa"), 0.0)
            chi = _safe_float(data.get("chi"), 0.0)
            sigma = _safe_float(data.get("sigma"), 0.0)
            alpha = _safe_float(data.get("alpha"), 0.0)

            do_broadcast = bool(data.get("broadcast", False))

            # immediate status update (echo params so UI can display what was verified)
            await _ws_send(
                websocket,
                {
                    "type": "lean_snapshot_status",
                    "status": "checking",
                    "ts": int(time.time() * 1000),
                    "steps": steps,
                    "dt_ms": dt_ms,
                    "spec_version": spec_version,
                    "scenario": scenario,
                    "kappa": kappa,
                    "chi": chi,
                    "sigma": sigma,
                    "alpha": alpha,
                },
            )

            cert = await asyncio.to_thread(
                _verify_snapshot_sync,
                steps=steps,
                dt_ms=dt_ms,
                spec_version=spec_version,
                scenario=scenario,
                kappa=kappa,
                chi=chi,
                sigma=sigma,
                alpha=alpha,
            )

            payload = {
                "type": "lean_snapshot_cert",
                "ts": int(time.time() * 1000),
                "ok": bool(cert.get("ok")),
                "cert": cert,
                # convenience top-level fields (what UI likely reads)
                "proof_hash_short": cert.get("proof_hash_short"),
                "elapsed_ms": cert.get("elapsed_ms"),
                "lean_file": cert.get("lean_file"),
                "stderr_tail": cert.get("stderr_tail", []),
                # echo proof-identity inputs so UI can confirm what was used
                "params": {
                    "steps": steps,
                    "dt_ms": dt_ms,
                    "spec_version": spec_version,
                    "scenario": scenario,
                    "kappa": kappa,
                    "chi": chi,
                    "sigma": sigma,
                    "alpha": alpha,
                },
                "server_time": datetime.utcnow().isoformat() + "Z",
            }

            await _ws_send(websocket, payload)
            if do_broadcast:
                await broadcast_qfc(payload)

    except WebSocketDisconnect:
        pass
    finally:
        QFC_CLIENTS.discard(websocket)