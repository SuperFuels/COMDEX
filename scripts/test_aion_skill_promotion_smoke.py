from __future__ import annotations

from backend.modules.aion_skills.registry import (
    get_global_skill_registry,
    register_builtin_demo_skills,
)


def main() -> None:
    reg = get_global_skill_registry()
    register_builtin_demo_skills(reg)

    sid = "skill.echo_text"

    print("has:", reg.has(sid))
    print("before:", reg.get_metadata(sid).to_dict())

    # promotion path
    p1 = reg.promote(sid, "verified")
    p2 = reg.promote(sid, "core")

    # invalid downgrade should fail
    p3 = reg.promote(sid, "experimental")

    # enable/disable checks
    d1 = reg.set_enabled(sid, False)
    resolve_disabled = reg.resolve(sid) is None
    d2 = reg.set_enabled(sid, True)
    resolve_enabled = reg.resolve(sid) is not None

    meta_after = reg.get_metadata(sid)
    print("promotions:", {"to_verified": p1, "to_core": p2, "downgrade_blocked": (p3 is False)})
    print("enable_disable:", {"disabled": d1, "resolve_disabled": resolve_disabled, "enabled": d2, "resolve_enabled": resolve_enabled})
    print("after:", meta_after.to_dict() if meta_after else None)
    print("registry_summary:", reg.telemetry_summary())

    ok = all([
        reg.has(sid),
        p1 is True,
        p2 is True,
        p3 is False,           # downgrade blocked
        d1 is True,
        resolve_disabled is True,
        d2 is True,
        resolve_enabled is True,
        meta_after is not None and meta_after.stage == "core",
        meta_after is not None and meta_after.enabled is True,
    ])
    print("promotion_smoke_ok:", ok)


if __name__ == "__main__":
    main()