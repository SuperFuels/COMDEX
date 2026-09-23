from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Dict

from .canonical import canonical_bytes
from .contracts import Capability, CapabilityKind, DeviceProfile, RiskLevel
from .identity import IdentityStore
from .delta import new_glyph_delta_stream
from .runtime import AionFabricRuntime, build_node_delta


def run_local_demo(base_dir: str | Path) -> Dict[str, Any]:
    """Exercise a mother, an edge node, and a restricted-device gateway."""
    root = Path(base_dir)
    summary_path = root / "demo_summary.json"
    database_path = root / "mother" / "fabric.sqlite3"
    if summary_path.exists() and database_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["status"] = AionFabricRuntime.bootstrap(root / "mother").status()
        return summary

    mother = AionFabricRuntime.bootstrap(root / "mother")

    fridge_identity = IdentityStore(root / "fridge_identity").load_or_create()
    fridge = DeviceProfile(
        node_id="node_demo_fridge",
        name="Demo Fridge",
        device_class="appliance",
        platform="embedded",
        cpu_count=1,
        memory_bytes=256 * 1024**2,
        can_install_runtime=True,
        can_host_model=False,
        is_mains_powered=True,
        transports=("ble", "wifi"),
        controls=("temperature.setpoint",),
    )
    mother.discover(fridge, fridge_identity.public_key_b64)
    mother.enroll(fridge.node_id, approved_by="demo_owner")
    capsule = mother.issue_capabilities(
        fridge.node_id,
        [
            Capability(
                "fridge.temperature.observe",
                CapabilityKind.OBSERVE,
                "Read cabinet temperature",
                schema={"temperature_c": "number"},
            ),
            Capability(
                "fridge.temperature.setpoint",
                CapabilityKind.CONTROL,
                "Change the temperature setpoint",
                risk=RiskLevel.MEDIUM,
                requires_approval=True,
                schema={"setpoint_c": {"type": "number", "minimum": 1, "maximum": 8}},
            ),
        ],
        approved_by="demo_owner",
    )

    tv_identity = IdentityStore(root / "tv_gateway_identity").load_or_create()
    tv = DeviceProfile(
        node_id="node_demo_tv",
        name="Restricted Demo TV",
        device_class="television",
        platform="restricted-tv",
        cpu_count=4,
        memory_bytes=2 * 1024**3,
        can_install_runtime=False,
        can_host_model=False,
        is_mains_powered=True,
        transports=("wifi", "hdmi-cec"),
        controls=("power", "volume", "input"),
    )
    mother.discover(tv, tv_identity.public_key_b64)
    mother.enroll(tv.node_id, approved_by="demo_owner")

    previous: Dict[str, Any] = {}
    current = {
        "temperature_c": 4.2,
        "door_open": False,
        "compressor": "running",
        "setpoint_c": 4.0,
        "sample_count": 1,
    }
    first = build_node_delta(
        node_id=fridge.node_id,
        identity=fridge_identity,
        previous=previous,
        current=current,
        sequence=1,
    )
    mother.accept_delta(first)

    updated = {**current, "temperature_c": 4.3, "sample_count": 2}
    second = build_node_delta(
        node_id=fridge.node_id,
        identity=fridge_identity,
        previous=current,
        current=updated,
        sequence=2,
    )
    mother.accept_delta(second)

    stream_states = [updated]
    stream_state = dict(updated)
    for sample in range(3, 1003):
        stream_state = {
            **stream_state,
            "temperature_c": round(4.3 + ((sample % 11) - 5) * 0.01, 2),
            "sample_count": sample,
        }
        stream_states.append(stream_state)
    stream = new_glyph_delta_stream(
        node_id=fridge.node_id,
        start_sequence=3,
        states=stream_states,
        identity=fridge_identity,
    )
    mother.accept_stream(stream)

    repeated_snapshots_bytes = sum(len(canonical_bytes(state)) for state in stream_states[1:])
    stream_bytes = len(canonical_bytes(stream.transport_envelope()))
    saving = 1 - (stream_bytes / repeated_snapshots_bytes)
    result = {
        "status": mother.status(),
        "fridge_role": mother.store.get_node(fridge.node_id).role.value,
        "tv_role": mother.store.get_node(tv.node_id).role.value,
        "capability_capsule": capsule.to_dict(),
        "latest_fridge_state": mother.store.state_for(fridge.node_id)[1],
        "transport": {
            "codec": "aion-glyph-stream+zlib-v1",
            "updates": 1000,
            "repeated_snapshot_bytes": repeated_snapshots_bytes,
            "signed_stream_envelope_bytes": stream_bytes,
            "saving_vs_repeated_raw_snapshots_percent": round(saving * 100, 2),
            "verified": stream.verify(fridge_identity.public_key_b64),
        },
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
