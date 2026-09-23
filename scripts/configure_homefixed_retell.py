#!/usr/bin/env python3
"""Create the governed Home Fixed Retell agent without placing a call."""

from __future__ import annotations

import json

from backend.modules.aion_business.runtime.retell_homefixed_agent import deploy_homefixed_agent


def main() -> None:
    result = deploy_homefixed_agent(publish=True)
    deployment = result["deployment"]
    print(json.dumps({
        "created": result["created"],
        "agent_id": deployment["agent_id"],
        "agent_name": deployment.get("agent_name"),
        "published": deployment.get("published"),
        "phone_number_connected": bool(deployment.get("phone_number")),
        "live_calls_enabled": bool(deployment.get("live_calls_enabled")),
    }, indent=2))


if __name__ == "__main__":
    main()

