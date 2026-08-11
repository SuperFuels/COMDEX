"""Narrow recovery for an unavailable NVIDIA Isaac 6.0 Franka asset key."""
from __future__ import annotations

import urllib.request
from typing import Any


BROKEN = "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.0/Isaac/IsaacLab/Robots/FrankaEmika/panda_instanceable.usd"
FALLBACK = "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac/IsaacLab/Robots/FrankaEmika/panda_instanceable.usd"


def recover_franka(cfg: Any) -> dict[str, str | int | bool]:
    current = str(cfg.scene.robot.spawn.usd_path)
    if current != BROKEN:
        return {"recovery_applied": False, "selected_url": current, "http_status": 0}
    request = urllib.request.Request(FALLBACK, method="HEAD",
                                     headers={"User-Agent": "AION-Isaac-Authority-Audit/1"})
    with urllib.request.urlopen(request, timeout=20) as response:
        status = int(response.status)
    if status != 200:
        raise RuntimeError(f"official_franka_fallback_unavailable:{status}")
    cfg.scene.robot.spawn.usd_path = FALLBACK
    return {"recovery_applied": True, "broken_url": BROKEN,
            "selected_url": FALLBACK, "http_status": status,
            "authority": "NVIDIA official S3 asset, prior public version"}
