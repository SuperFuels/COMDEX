#!/usr/bin/env python3
from __future__ import annotations
import os, plistlib, subprocess, sys
from pathlib import Path

LABEL = "ai.tessaris.security-sentinel"
repo = Path(__file__).resolve().parents[2]
state = Path("~/.tessaris/security-sentinel").expanduser()
state.mkdir(parents=True, exist_ok=True, mode=0o700)
roots = [p for p in (repo, Path("~/Documents/Tessaris").expanduser(), Path("~/Downloads").expanduser()) if p.exists()]
plist = {"Label": LABEL, "ProgramArguments": [sys.executable, str(repo / "backend/scripts/aion_security_sentinel_agent.py")],
         "RunAtLoad": True, "KeepAlive": True, "ThrottleInterval": 10,
         "EnvironmentVariables": {"TESSARIS_SENTINEL_STATE_DIR": str(state), "TESSARIS_SENTINEL_WATCH_ROOTS": os.pathsep.join(map(str, roots)), "TESSARIS_SENTINEL_INTERVAL": "5"},
         "StandardOutPath": str(state / "agent.log"), "StandardErrorPath": str(state / "agent-error.log")}
target = Path("~/Library/LaunchAgents").expanduser() / f"{LABEL}.plist"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_bytes(plistlib.dumps(plist)); target.chmod(0o600)
domain = f"gui/{os.getuid()}"
subprocess.run(["/bin/launchctl", "bootout", domain, str(target)], capture_output=True)
result = subprocess.run(["/bin/launchctl", "bootstrap", domain, str(target)], capture_output=True, text=True)
if result.returncode: raise SystemExit(result.stderr.strip() or "launchctl_bootstrap_failed")
subprocess.run(["/bin/launchctl", "enable", f"{domain}/{LABEL}"], check=False)
print(target)
