from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


_PRESET = re.compile(r"^(?:off|fan_auto|(?:cool|heat|dry)_(?:1[6-9]|2[0-9]|30))$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LocalInfraredClimateGateway:
    """Local-only learned-IR bridge with bounded Toshiba climate presets.

    The BroadLink dependency is deliberately lazy: Pilot remains usable before
    hardware is present. Device discovery and learned-code transport can also be
    injected for deterministic tests.
    """

    def __init__(
        self,
        base_dir: str | Path,
        *,
        discover: Callable[..., list[Any]] | None = None,
        minimum_send_interval_seconds: float = 1.0,
    ) -> None:
        self.root = Path(base_dir) / "infrared" / "climate"
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.root, 0o700)
        except OSError:
            pass
        self.state_path = self.root / "gateway.json"
        self.codes_path = self.root / "learned_codes.json"
        self._discover = discover
        self.minimum_send_interval_seconds = max(0.0, float(minimum_send_interval_seconds))

    @staticmethod
    def validate_preset(value: str) -> str:
        preset = re.sub(r"[^a-z0-9_]+", "_", str(value).strip().lower()).strip("_")
        if not _PRESET.fullmatch(preset):
            raise ValueError("Use off, fan_auto, or a cool/heat/dry preset from 16 to 30 degrees")
        return preset

    def _read(self, path: Path, default: dict[str, Any]) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else dict(default)
        except (OSError, json.JSONDecodeError):
            return dict(default)

    def _write(self, path: Path, value: dict[str, Any]) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)

    def _discover_devices(self, timeout: float = 3.0) -> list[Any]:
        discover = self._discover
        if discover is None:
            try:
                import broadlink  # type: ignore
            except ImportError as exc:
                raise RuntimeError("The local BroadLink driver is not installed") from exc
            discover = broadlink.discover
        devices = discover(timeout=max(1.0, min(float(timeout), 5.0)))
        return list(devices or [])[:16]

    @staticmethod
    def _device_record(device: Any) -> dict[str, Any]:
        host_value = getattr(device, "host", ("", 0))
        host = str(host_value[0] if isinstance(host_value, (tuple, list)) else host_value)
        mac_value = getattr(device, "mac", b"")
        mac = bytes(mac_value).hex() if isinstance(mac_value, (bytes, bytearray)) else str(mac_value)
        return {
            "host": host,
            "mac": re.sub(r"[^0-9a-f]", "", mac.lower())[:32],
            "device_type": int(getattr(device, "devtype", 0) or 0),
            "model": type(device).__name__,
        }

    def discover(self, *, timeout: float = 3.0) -> dict[str, Any]:
        found = []
        for device in self._discover_devices(timeout):
            record = self._device_record(device)
            if record["host"] and record["mac"]:
                found.append(record)
        current = self._read(self.state_path, {})
        if len(found) == 1:
            current.update({"device": found[0], "selected_at": _now()})
            self._write(self.state_path, current)
        return {
            "found": found,
            "selected": current.get("device"),
            "requires_initial_wifi_provisioning": not bool(found),
        }

    def select(self, mac: str) -> dict[str, Any]:
        wanted = re.sub(r"[^0-9a-f]", "", str(mac).lower())
        devices = self._discover_devices()
        for device in devices:
            record = self._device_record(device)
            if record["mac"] == wanted:
                state = self._read(self.state_path, {})
                state.update({"device": record, "selected_at": _now()})
                self._write(self.state_path, state)
                return record
        raise LookupError("That infrared gateway is not currently reachable on the local network")

    def _selected_device(self) -> Any:
        selected = dict(self._read(self.state_path, {}).get("device") or {})
        if not selected.get("mac"):
            raise RuntimeError("No local infrared gateway is selected")
        for device in self._discover_devices():
            if self._device_record(device).get("mac") == selected["mac"]:
                auth = getattr(device, "auth", None)
                if callable(auth) and auth() is False:
                    raise PermissionError("The local infrared gateway rejected authentication")
                return device
        raise RuntimeError("The local infrared gateway is not reachable")

    def begin_learning(self, preset: str) -> dict[str, Any]:
        preset = self.validate_preset(preset)
        device = self._selected_device()
        device.enter_learning()
        state = self._read(self.state_path, {})
        state["pending_learning"] = {"preset": preset, "started_at": _now()}
        self._write(self.state_path, state)
        return {
            "preset": preset,
            "learning": True,
            "instruction": "Point the WH-UC01NE at the infrared gateway and press the exact remote command once.",
        }

    def capture_learning(self) -> dict[str, Any]:
        state = self._read(self.state_path, {})
        pending = dict(state.get("pending_learning") or {})
        preset = self.validate_preset(str(pending.get("preset") or ""))
        data = self._selected_device().check_data()
        if not isinstance(data, (bytes, bytearray)) or not 8 <= len(data) <= 4096:
            raise RuntimeError("No valid infrared command was captured; press the remote button and try Capture again")
        raw = bytes(data)
        codes = self._read(self.codes_path, {"schema_version": "pilot.ir-climate-codes.v1", "codes": {}})
        code_map = dict(codes.get("codes") or {})
        code_map[preset] = {
            "data_b64": base64.b64encode(raw).decode("ascii"),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "learned_at": _now(),
        }
        codes["codes"] = code_map
        self._write(self.codes_path, codes)
        state.pop("pending_learning", None)
        self._write(self.state_path, state)
        return {"preset": preset, **{key: code_map[preset][key] for key in ("sha256", "bytes", "learned_at")}}

    def send(self, preset: str) -> dict[str, Any]:
        preset = self.validate_preset(preset)
        codes = self._read(self.codes_path, {"codes": {}})
        record = dict((codes.get("codes") or {}).get(preset) or {})
        if not record:
            raise LookupError(f"The {preset} Toshiba preset has not been learned")
        try:
            data = base64.b64decode(str(record["data_b64"]), validate=True)
        except Exception as exc:
            raise RuntimeError("The learned infrared command is corrupt") from exc
        if not 8 <= len(data) <= 4096 or hashlib.sha256(data).hexdigest() != record.get("sha256"):
            raise RuntimeError("The learned infrared command failed its integrity check")
        state = self._read(self.state_path, {})
        previous = str(state.get("last_sent_at") or "")
        if previous:
            try:
                elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(previous)).total_seconds()
            except ValueError:
                elapsed = self.minimum_send_interval_seconds
            if elapsed < self.minimum_send_interval_seconds:
                raise RuntimeError("Please wait a moment before sending another infrared command")
        self._selected_device().send_data(data)
        sent_at = _now()
        state.update({"last_sent_at": sent_at, "last_active_preset": preset if preset != "off" else state.get("last_active_preset")})
        self._write(self.state_path, state)
        return {
            "preset": preset,
            "sent_at": sent_at,
            "code_sha256": record["sha256"],
            "transport_delivered": True,
            "air_conditioner_state_verified": False,
            "verification": "Infrared is one-way; confirm on the Toshiba display or with a separate temperature sensor.",
        }

    def send_last_active(self) -> dict[str, Any]:
        preset = str(self._read(self.state_path, {}).get("last_active_preset") or "")
        if not preset:
            raise LookupError("No previously used active Toshiba preset is available")
        return self.send(preset)

    def snapshot(self) -> dict[str, Any]:
        state = self._read(self.state_path, {})
        codes = dict(self._read(self.codes_path, {"codes": {}}).get("codes") or {})
        return {
            "device": state.get("device"),
            "connected": bool(state.get("device")),
            "pending_learning": state.get("pending_learning"),
            "learned_presets": [
                {"preset": name, "sha256": value.get("sha256"), "bytes": value.get("bytes"), "learned_at": value.get("learned_at")}
                for name, value in sorted(codes.items())
                if isinstance(value, dict)
            ],
            "last_sent_at": state.get("last_sent_at"),
            "last_active_preset": state.get("last_active_preset"),
            "raw_codes_exposed": False,
            "cloud_credentials_required_for_operation": False,
            "state_verification": "not_available_from_ir",
            "target": {"brand": "Toshiba", "model": "RAS-24J2KVG-E", "remote": "WH-UC01NE"},
        }
