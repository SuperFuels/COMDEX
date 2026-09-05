from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import ssl
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse
from uuid import uuid4

from websockets.sync.client import ClientConnection, connect
from websockets.exceptions import InvalidHandshake

from .canonical import canonical_bytes, utc_now_iso


PAIRING_PERMISSIONS = [
    "CONTROL_AUDIO",
    "CONTROL_INPUT_TEXT",
    "CONTROL_INPUT_MEDIA_PLAYBACK",
    "CONTROL_INPUT_TV",
    "CONTROL_MOUSE_AND_KEYBOARD",
    "LAUNCH",
    "READ_APP_STATUS",
    "READ_CURRENT_CHANNEL",
    "READ_SETTINGS",
    "READ_POWER_STATE",
    "READ_RUNNING_APPS",
    "READ_INSTALLED_APPS",
    "READ_INPUT_DEVICE_LIST",
    "READ_NETWORK_STATE",
]


@dataclass(slots=True)
class WebOsPairingReceipt:
    receipt_id: str
    node_id: str
    host: str
    paired: bool
    reused_client_key: bool
    permissions_requested: list[str]
    proof_action: str
    proof_values: Dict[str, Any]
    request_hash: str
    response_hash: str
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WebOsIntegrationReceipt:
    receipt_id: str
    node_id: str
    host: str
    connected_surfaces: list[str]
    read_results: Dict[str, Any]
    read_errors: Dict[str, str]
    volume_round_trip: Dict[str, Any]
    request_hash: str
    response_hash: str
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WebOsActionReceipt:
    receipt_id: str
    node_id: str
    action: str
    arguments: Dict[str, Any]
    before: Dict[str, Any]
    after: Dict[str, Any]
    verified: bool
    request_hash: str
    response_hash: str
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WebOsGateway:
    """Least-privilege LG webOS SSAP pairing and observe-only proof client."""

    MAX_MESSAGE_BYTES = 1024 * 1024

    @staticmethod
    def preferred_games_application(installed_ids: set[str]) -> tuple[str, str] | None:
        """Choose the native NVIDIA surface before LG's aggregate games portal."""
        candidates = (
            ("com.geforcenow.play", "GeForce NOW"),
            ("com.twin.app.gamingportal", "LG Gaming Portal"),
        )
        return next((item for item in candidates if item[0] in installed_ids), None)

    def __init__(self, pairing_dir: str | Path) -> None:
        self.pairing_dir = Path(pairing_dir)
        self.pairing_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def validate_host(host: str) -> str:
        address = ipaddress.ip_address(host.split("%", 1)[0])
        if not (address.is_private or address.is_link_local or address.is_loopback):
            raise ValueError("webOS pairing is limited to a directly reachable local-network address")
        return str(address)

    def _state_path(self, node_id: str) -> Path:
        if not node_id.startswith("node_discovered_"):
            raise ValueError("Pairing state requires a discovered Fabric node")
        return self.pairing_dir / f"{node_id}.json"

    def _load_key(self, node_id: str, host: str) -> str | None:
        path = self._state_path(node_id)
        if not path.exists():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("host") != host:
            return None
        return str(value.get("client_key") or "") or None

    def _save_key(self, node_id: str, host: str, client_key: str) -> None:
        path = self._state_path(node_id)
        temporary = path.with_suffix(".tmp")
        payload = {
            "node_id": node_id,
            "host": host,
            "client_key": client_key,
            "paired_at": utc_now_iso(),
        }
        temporary.write_bytes(canonical_bytes(payload))
        temporary.chmod(0o600)
        os.replace(temporary, path)
        path.chmod(0o600)

    def migrate_paired_host(self, *, node_id: str, old_host: str, new_host: str) -> None:
        """Move an existing pairing key after discovery proves the same device changed IP."""
        old_host = self.validate_host(old_host)
        new_host = self.validate_host(new_host)
        if old_host == new_host:
            return
        path = self._state_path(node_id)
        if not path.exists():
            raise PermissionError("No saved webOS pairing is available to migrate")
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("node_id") != node_id or value.get("host") != old_host or not value.get("client_key"):
            raise PermissionError("Saved webOS pairing does not match the previously verified host")
        value["host"] = new_host
        value["host_migrated_at"] = utc_now_iso()
        temporary = path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(value))
        temporary.chmod(0o600)
        os.replace(temporary, path)
        path.chmod(0o600)

    @staticmethod
    def _receive_json(connection: ClientConnection, *, timeout: float) -> Dict[str, Any]:
        raw = connection.recv(timeout=timeout)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if len(raw.encode("utf-8")) > WebOsGateway.MAX_MESSAGE_BYTES:
            raise ValueError("webOS response exceeded the configured size limit")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("webOS returned a non-object response")
        return value

    @staticmethod
    def _connect(host: str, *, open_timeout: float = 4) -> ClientConnection:
        try:
            return connect(
                f"ws://{host}:3000",
                open_timeout=open_timeout,
                close_timeout=2,
                max_size=WebOsGateway.MAX_MESSAGE_BYTES,
                proxy=None,
            )
        except (OSError, InvalidHandshake):
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return connect(
                f"wss://{host}:3001",
                ssl=context,
                open_timeout=open_timeout,
                close_timeout=2,
                max_size=WebOsGateway.MAX_MESSAGE_BYTES,
                proxy=None,
            )

    @classmethod
    def probe_endpoint(cls, host: str, *, timeout: float = 1.2) -> Dict[str, Any]:
        """Prove that a socket is webOS SSAP, not merely an open TCP port."""
        host = cls.validate_host(host)
        with cls._connect(host, open_timeout=max(0.5, min(float(timeout), 3.0))) as connection:
            cls._send(connection, {"id": "pilot_health_hello", "type": "hello", "payload": {}})
            response = cls._receive_json(connection, timeout=max(0.5, min(float(timeout), 3.0)))
        if response.get("type") not in {"hello", "response"}:
            raise RuntimeError("The endpoint did not identify itself as a webOS control service")
        return {"connected": True, "host": host, "protocol": "webos_ssap"}

    def check_paired_connection(self, *, node_id: str, host: str) -> Dict[str, Any]:
        """Verify the saved authorization through a real registered SSAP session."""
        with self._registered_connection(node_id=node_id, host=host):
            return {"connected": True, "host": self.validate_host(host), "protocol": "paired_webos_ssap"}

    @staticmethod
    def _send_pointer_buttons(*, socket_path: str, host: str, buttons: list[str]) -> None:
        parsed = urlparse(socket_path)
        if parsed.scheme not in {"ws", "wss"} or parsed.hostname != host or parsed.port not in {3000, 3001}:
            raise ValueError("The TV returned an invalid local pointer socket")
        allowed = {"UP", "DOWN", "LEFT", "RIGHT", "ENTER", "BACK", "HOME"}
        if not buttons or any(button not in allowed for button in buttons) or len(buttons) > 12:
            raise ValueError("Remote navigation is outside the bounded button policy")
        options: Dict[str, Any] = {
            "open_timeout": 4,
            "close_timeout": 2,
            "max_size": WebOsGateway.MAX_MESSAGE_BYTES,
            "proxy": None,
        }
        if parsed.scheme == "wss":
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            options["ssl"] = context
        with connect(socket_path, **options) as pointer:
            for button in buttons:
                pointer.send(f"type:button\nname:{button}\n\n")
                time.sleep(0.18)

    @staticmethod
    def _send_pointer_button_phases(
        *, socket_path: str, host: str, phases: list[tuple[list[str], float]]
    ) -> None:
        """Send a bounded staged route over one LG-issued pointer socket."""
        parsed = urlparse(socket_path)
        if parsed.scheme not in {"ws", "wss"} or parsed.hostname != host or parsed.port not in {3000, 3001}:
            raise ValueError("The TV returned an invalid local pointer socket")
        allowed = {"UP", "DOWN", "LEFT", "RIGHT", "ENTER", "BACK", "HOME"}
        total = sum(len(buttons) for buttons, _ in phases)
        if (
            not phases or len(phases) > 4 or total > 36
            or any(not buttons or len(buttons) > 12 for buttons, _ in phases)
            or any(button not in allowed for buttons, _ in phases for button in buttons)
            or any(float(delay) < 0 or float(delay) > 4.0 for _, delay in phases)
        ):
            raise ValueError("Staged remote navigation is outside the bounded button policy")
        options: Dict[str, Any] = {
            "open_timeout": 4,
            "close_timeout": 2,
            "max_size": WebOsGateway.MAX_MESSAGE_BYTES,
            "proxy": None,
        }
        if parsed.scheme == "wss":
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            options["ssl"] = context
        with connect(socket_path, **options) as pointer:
            for buttons, delay in phases:
                for button in buttons:
                    pointer.send(f"type:button\nname:{button}\n\n")
                    time.sleep(0.18)
                if delay:
                    time.sleep(float(delay))

    @staticmethod
    def _send_pointer_event(
        *, socket_path: str, host: str, kind: str, dx: int = 0, dy: int = 0
    ) -> None:
        parsed = urlparse(socket_path)
        if parsed.scheme not in {"ws", "wss"} or parsed.hostname != host or parsed.port not in {3000, 3001}:
            raise ValueError("The TV returned an invalid local pointer socket")
        if kind not in {"move", "click"}:
            raise ValueError("Unsupported pointer event")
        if abs(dx) > 240 or abs(dy) > 240:
            raise ValueError("Pointer movement exceeds the bounded controller policy")
        options: Dict[str, Any] = {
            "open_timeout": 4,
            "close_timeout": 2,
            "max_size": WebOsGateway.MAX_MESSAGE_BYTES,
            "proxy": None,
        }
        if parsed.scheme == "wss":
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            options["ssl"] = context
        with connect(socket_path, **options) as pointer:
            if kind == "move":
                pointer.send(f"type:move\ndx:{dx}\ndy:{dy}\ndown:0\n\n")
            else:
                pointer.send("type:click\n\n")

    @staticmethod
    def _send(connection: ClientConnection, value: Dict[str, Any]) -> bytes:
        payload = canonical_bytes(value)
        connection.send(payload.decode("utf-8"))
        return payload

    @contextmanager
    def _registered_connection(self, *, node_id: str, host: str):
        host = self.validate_host(host)
        client_key = self._load_key(node_id, host)
        if not client_key:
            raise PermissionError("LG webOS pairing must be completed first")
        with self._connect(host) as connection:
            self._send(connection, {"id": "hello", "type": "hello", "payload": {}})
            self._receive_json(connection, timeout=8)
            self._send(
                connection,
                {
                    "id": "action_preflight",
                    "type": "request",
                    "uri": "ssap://system/getSystemInfo",
                    "payload": {},
                },
            )
            self._receive_json(connection, timeout=8)
            self._send(
                connection,
                {
                    "id": "register_aion_action",
                    "type": "register",
                    "payload": {
                        "forcePairing": False,
                        "pairingType": "PROMPT",
                        "manifest": {
                            "manifestVersion": 1,
                            "appVersion": "0.47.0",
                            "permissions": PAIRING_PERMISSIONS,
                        },
                        "client-key": client_key,
                    },
                },
            )
            response = self._receive_json(connection, timeout=10)
            if response.get("type") != "registered":
                raise PermissionError("The saved LG authorization must be approved again")
            yield connection

    def execute_governed_action(
        self,
        *,
        node_id: str,
        host: str,
        action: str,
        arguments: Dict[str, Any],
        maximum_voice_volume: int = 35,
    ) -> WebOsActionReceipt:
        allowed = {
            "observe_state",
            "get_volume",
            "set_volume",
            "change_volume",
            "set_mute",
            "media_play",
            "media_pause",
            "media_stop",
            "switch_input",
            "launch_app",
            "launch_games",
            "open_url",
            "remote_button",
            "pointer_move",
            "pointer_click",
            "netflix_profile",
            "netflix_profile_menu",
            "netflix_search",
            "open_public_url",
        }
        if action not in allowed:
            raise PermissionError(f"Action {action!r} is outside the governed webOS adapter")
        requests = bytearray()
        responses = bytearray()
        sequence = 0

        with self._registered_connection(node_id=node_id, host=host) as connection:
            def request(uri: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
                nonlocal sequence
                sequence += 1
                message = {
                    "id": f"aion_action_{sequence}",
                    "type": "request",
                    "uri": f"ssap://{uri}",
                    "payload": payload or {},
                }
                requests.extend(self._send(connection, message))
                response = self._receive_json(connection, timeout=12)
                responses.extend(canonical_bytes(response))
                if response.get("type") == "error" or not response.get("payload", {}).get("returnValue"):
                    raise RuntimeError(str(response.get("error") or "request rejected"))
                return dict(response.get("payload", {}))

            before: Dict[str, Any] = {}
            after: Dict[str, Any] = {}
            verified = False
            if action == "observe_state":
                foreground = request("com.webos.applicationManager/getForegroundAppInfo")
                volume = request("audio/getVolume")
                app_id = str(foreground.get("appId") or foreground.get("id") or "unknown")[:160]
                app_title = str(foreground.get("appName") or foreground.get("title") or app_id)[:160]
                after = {
                    "foreground_app_id": app_id,
                    "foreground_app_title": app_title,
                    "volume": self._volume_from_payload(volume),
                    "source": "webos_foreground_app_and_audio_state",
                    "pixel_vision": False,
                }
                verified = app_id != "unknown"
            elif action in {"get_volume", "set_volume", "change_volume"}:
                initial = request("audio/getVolume")
                current = self._volume_from_payload(initial)
                before = {"volume": current}
                if action == "get_volume":
                    after = before
                    verified = current is not None
                else:
                    if current is None:
                        raise RuntimeError("The TV did not provide its current volume")
                    target = self.voice_volume_target(
                        current=current,
                        action=action,
                        arguments=arguments,
                        maximum=maximum_voice_volume,
                    )
                    request("audio/setVolume", {"volume": target})
                    observed = self._volume_from_payload(request("audio/getVolume"))
                    after = {"volume": observed, "requested_volume": target}
                    verified = observed == target
            elif action == "set_mute":
                status = request("audio/getStatus")
                before = {"muted": bool(status.get("mute"))}
                target_mute = bool(arguments["muted"])
                request("audio/setMute", {"mute": target_mute})
                observed = request("audio/getStatus")
                after = {"muted": bool(observed.get("mute"))}
                verified = after["muted"] == target_mute
            elif action.startswith("media_"):
                endpoint = {
                    "media_play": "media.controls/play",
                    "media_pause": "media.controls/pause",
                    "media_stop": "media.controls/stop",
                }[action]
                result = request(endpoint)
                after = {"returnValue": result.get("returnValue")}
                verified = True
            elif action == "switch_input":
                input_id = str(arguments.get("input_id", ""))
                if input_id not in {"HDMI_1", "HDMI_2", "HDMI_3", "HDMI_4"}:
                    raise ValueError("Voice input switching is limited to HDMI 1-4")
                request("tv/switchInput", {"inputId": input_id})
                after = {"input_id": input_id}
                verified = True
            elif action == "launch_app":
                app_id = str(arguments.get("app_id", ""))
                if app_id not in {"netflix", "youtube.leanback.v4"}:
                    raise ValueError("Only explicitly mapped voice apps may be launched")
                result = request("com.webos.applicationManager/launch", {"id": app_id})
                time.sleep(0.6)
                foreground = request("com.webos.applicationManager/getForegroundAppInfo")
                observed_app = str(foreground.get("appId") or foreground.get("id") or "")
                after = {
                    "app_id": app_id,
                    "foreground_app_id": observed_app,
                    "returnValue": result.get("returnValue"),
                    "screen_effect_observed": observed_app == app_id,
                }
                verified = observed_app == app_id
            elif action == "launch_games":
                foreground_before = request("com.webos.applicationManager/getForegroundAppInfo")
                before_app = str(foreground_before.get("appId") or foreground_before.get("id") or "")
                applications = request("com.webos.applicationManager/listApps")
                installed_ids = {
                    str(app.get("id") or "")
                    for app in list(applications.get("apps") or [])
                    if isinstance(app, dict)
                }
                # Pilot Games is the NVIDIA experience. Prefer its native app;
                # use LG's aggregate Gaming Portal only when GeForce NOW is not
                # installed on the television.
                selected = self.preferred_games_application(installed_ids)
                if selected is None:
                    raise RuntimeError("No supported native cloud-gaming application is installed on this TV")
                app_id, app_title = selected
                # An external URL left in LG Browser can reclaim focus while a
                # webOS web application starts. Normalize through Home first so
                # the native NVIDIA application owns the new launch lifecycle.
                if before_app == "com.webos.app.browser":
                    request("com.webos.applicationManager/launch", {"id": "com.webos.app.home"})
                    time.sleep(0.8)
                result = request("com.webos.applicationManager/launch", {"id": app_id})
                observations: list[str] = []
                # Some LG webOS applications report an empty foreground during
                # their startup transition. Require the selected native surface
                # to remain foreground twice, rather than trusting launch ACK.
                stable = 0
                for _ in range(12):
                    time.sleep(0.5)
                    foreground = request("com.webos.applicationManager/getForegroundAppInfo")
                    observed_app = str(foreground.get("appId") or foreground.get("id") or "")
                    observations.append(observed_app)
                    stable = stable + 1 if observed_app == app_id else 0
                    if stable >= 2:
                        break
                after = {
                    "foreground_app_before": before_app,
                    "app_id": app_id,
                    "app_title": app_title,
                    "foreground_app_id": observations[-1] if observations else "",
                    "foreground_observations": observations,
                    "returnValue": result.get("returnValue"),
                    "screen_effect_observed": stable >= 2,
                    "contract": "native_lg_gaming_surface_v1",
                }
                verified = bool(result.get("returnValue")) and stable >= 2
            elif action == "open_url":
                target = str(arguments.get("target", ""))
                parsed = urlparse(target)
                if parsed.scheme != "http" or not parsed.hostname or parsed.port != 8766:
                    raise ValueError("TV Canvas links must use the dedicated local display port")
                address = ipaddress.ip_address(parsed.hostname)
                if not address.is_private or address.is_loopback or not parsed.path.startswith("/tv/"):
                    raise ValueError("TV Canvas links must target a private LAN display session")
                result = request("system.launcher/open", {"target": target})
                time.sleep(0.5)
                foreground = request("com.webos.applicationManager/getForegroundAppInfo")
                observed_app = str(foreground.get("appId") or foreground.get("id") or "")
                after = {
                    "opened": True,
                    "returnValue": result.get("returnValue"),
                    "foreground_app_id": observed_app,
                    "screen_effect_observed": bool(observed_app),
                }
                verified = bool(result.get("returnValue")) and bool(observed_app)
            elif action in {"remote_button", "netflix_profile", "netflix_profile_menu", "pointer_move", "pointer_click"}:
                if action in {"pointer_move", "pointer_click"}:
                    pointer = request("com.webos.service.networkinput/getPointerInputSocket")
                    socket_path = str(pointer.get("socketPath") or "")
                    dx = int(arguments.get("dx", 0))
                    dy = int(arguments.get("dy", 0))
                    self._send_pointer_event(
                        socket_path=socket_path,
                        host=self.validate_host(host),
                        kind="move" if action == "pointer_move" else "click",
                        dx=dx,
                        dy=dy,
                    )
                    after = {
                        "pointer_event": "move" if action == "pointer_move" else "click",
                        "transport_verified": True,
                        "screen_effect_observed": False,
                    }
                    verified = True
                elif action == "remote_button":
                    button = str(arguments.get("button", "")).upper()
                    if button not in {"UP", "DOWN", "LEFT", "RIGHT", "ENTER", "BACK", "HOME"}:
                        raise ValueError("Remote navigation is limited to Up, Down, Left, Right, Enter, Back, and Home")
                    buttons = [button]
                else:
                    profile_menu_only = action == "netflix_profile_menu"
                    profile_index = int(arguments.get("profile_index", 0))
                    if not profile_menu_only and profile_index not in {1, 2, 3, 4, 5}:
                        raise ValueError("Netflix profile position must be between one and five")
                    foreground = request("com.webos.applicationManager/getForegroundAppInfo")
                    foreground_id = str(foreground.get("appId") or foreground.get("id") or "").lower()
                    if foreground_id != "netflix":
                        raise RuntimeError("Switch profile requires Netflix to be open")
                    pointer = request("com.webos.service.networkinput/getPointerInputSocket")
                    socket_path = str(pointer.get("socketPath") or "")
                    # Netflix exposes no supported profile-switch API on this TV.
                    # Use a bounded, auditable route through its visible top menu:
                    # leave playback/detail, force the left rail, select the profile
                    # control at its top, then choose the requested position.
                    open_phases = [
                        (["BACK"], 0.7),
                        (["LEFT"] * 6, 0.5),
                        ((["UP"] * 8) + ["ENTER"], 3.0),
                    ]
                    # Netflix initially focuses the currently active profile,
                    # not necessarily the first profile. Normalize focus to the
                    # top of the bounded vertical list before selecting the
                    # requested absolute position.
                    select_profile = (
                        self.netflix_profile_selection_buttons(profile_index)
                        if not profile_menu_only else []
                    )
                    if bool(arguments.get("chooser_visible")) and not profile_menu_only:
                        phases = [
                            (select_profile, 0.0),
                        ]
                    else:
                        phases = open_phases if profile_menu_only else open_phases + [
                        (select_profile, 0.0),
                        ]
                    delivered: list[str] = []
                    self._send_pointer_button_phases(
                        socket_path=socket_path,
                        host=self.validate_host(host),
                        phases=phases,
                    )
                    for phase, _ in phases:
                        delivered.extend(phase)
                    after = {
                        "buttons_delivered": delivered,
                        "profile_index": profile_index,
                        "route": (
                            "netflix_profile_chooser_open_v1" if profile_menu_only
                            else "netflix_visible_chooser_select_v3" if bool(arguments.get("chooser_visible"))
                            else "netflix_visible_profile_menu_v4"
                        ),
                        "transport_verified": True,
                        "screen_effect_observed": False,
                    }
                    verified = True
                    buttons = []
                if action not in {"pointer_move", "pointer_click"}:
                    if buttons:
                        pointer = request("com.webos.service.networkinput/getPointerInputSocket")
                        socket_path = str(pointer.get("socketPath") or "")
                        self._send_pointer_buttons(socket_path=socket_path, host=self.validate_host(host), buttons=buttons)
                        after = {
                            "buttons_delivered": buttons,
                            "transport_verified": True,
                            "screen_effect_observed": False,
                        }
                        verified = True
            elif action == "netflix_search":
                query = " ".join(str(arguments.get("query") or "").split()).strip()[:120]
                title = " ".join(str(arguments.get("title") or "").split()).strip()[:160]
                title_id = str(arguments.get("title_id") or "")
                if len(query) < 1:
                    raise ValueError("Netflix search text is empty")
                if not title_id.isdigit() or not (5 <= len(title_id) <= 12):
                    raise ValueError("Netflix search requires a verified numeric title ID")
                applications = request("com.webos.applicationManager/listApps")
                netflix = next(
                    (
                        app for app in list(applications.get("apps") or [])
                        if str(app.get("id") or "").lower() == "netflix"
                    ),
                    None,
                )
                if not netflix or not netflix.get("inAppVoiceIntent") or not netflix.get("handlesRelaunch"):
                    raise RuntimeError("This Netflix installation does not advertise governed in-app search")
                content_id = (
                    "m=http%3A%2F%2Fapi.netflix.com%2Fcatalog%2Ftitles%2Fmovies%2F"
                    f"{title_id}&source_type=4"
                )
                launched = request("system.launcher/launch", {"id": "netflix", "contentId": content_id})
                time.sleep(0.6)
                foreground = request("com.webos.applicationManager/getForegroundAppInfo")
                observed_app = str(foreground.get("appId") or foreground.get("id") or "")
                after = {
                    "app_id": "netflix",
                    "query": query,
                    "title": title,
                    "title_id": title_id,
                    "contract": "netflix_content_id_deeplink",
                    "intent_accepted": bool(launched.get("returnValue")),
                    "foreground_app_id": observed_app,
                    "screen_effect_observed": observed_app == "netflix",
                }
                verified = after["intent_accepted"] and after["screen_effect_observed"]
            elif action == "open_public_url":
                target = str(arguments.get("target", ""))
                parsed = urlparse(target)
                if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                    raise ValueError("Research results must be credential-free HTTPS URLs")
                if parsed.port not in {None, 443} or parsed.hostname.lower() in {"localhost", "localhost.localdomain"}:
                    raise ValueError("The research result URL is outside the public browser policy")
                try:
                    literal = ipaddress.ip_address(parsed.hostname)
                except ValueError:
                    literal = None
                if literal is not None and (literal.is_private or literal.is_loopback or literal.is_link_local):
                    raise ValueError("Private network research result URLs are blocked")
                result = request("system.launcher/open", {"target": target})
                after = {"opened": True, "host": parsed.hostname, "returnValue": result.get("returnValue")}
                verified = True
            if not verified:
                raise RuntimeError(f"The TV did not verify {action}: before={before}, after={after}")

        return WebOsActionReceipt(
            receipt_id=f"webos_action_{uuid4().hex}",
            node_id=node_id,
            action=action,
            arguments=arguments,
            before=before,
            after=after,
            verified=verified,
            request_hash=hashlib.sha256(requests).hexdigest(),
            response_hash=hashlib.sha256(responses).hexdigest(),
        )

    def send_ephemeral_text(
        self,
        *,
        node_id: str,
        host: str,
        text: str,
        replace: bool = True,
    ) -> Dict[str, Any]:
        """Insert private phone text into the focused TV field without retaining it.

        This deliberately does not create a normal action receipt: neither the
        plaintext nor a reusable hash of a password belongs in Fabric history.
        """
        if not isinstance(text, str) or not text or len(text) > 320:
            raise ValueError("Private keyboard text must contain 1 to 320 characters")
        with self._registered_connection(node_id=node_id, host=host) as connection:
            message = {
                "id": f"aion_private_keyboard_{uuid4().hex}",
                "type": "request",
                "uri": "ssap://com.webos.service.ime/insertText",
                "payload": {"text": text, "replace": bool(replace)},
            }
            self._send(connection, message)
            response = self._receive_json(connection, timeout=12)
            payload = dict(response.get("payload") or {})
            if response.get("type") == "error" or not payload.get("returnValue"):
                raise RuntimeError("The focused television field did not accept private keyboard input")
        return {"accepted": True, "characters_delivered": len(text), "retained": False}

    def pair_and_prove_read_only(
        self,
        *,
        node_id: str,
        host: str,
        approval_timeout: float = 90.0,
        force_pairing: bool = False,
    ) -> WebOsPairingReceipt:
        host = self.validate_host(host)
        existing_key = self._load_key(node_id, host)
        request_material = bytearray()
        response_material = bytearray()
        with self._connect(host) as connection:
            request_material.extend(self._send(connection, {"id": "hello", "type": "hello", "payload": {}}))
            hello = self._receive_json(connection, timeout=8)
            response_material.extend(canonical_bytes(hello))

            system_request = {
                "id": "system_info_before_pairing",
                "type": "request",
                "uri": "ssap://system/getSystemInfo",
                "payload": {},
            }
            request_material.extend(self._send(connection, system_request))
            system_response = self._receive_json(connection, timeout=8)
            response_material.extend(canonical_bytes(system_response))

            registration = {
                "id": "register_aion_readonly",
                "type": "register",
                "payload": {
                    "forcePairing": force_pairing,
                    "pairingType": "PROMPT",
                    "manifest": {
                        "manifestVersion": 1,
                        "appVersion": "0.47.0",
                        "permissions": PAIRING_PERMISSIONS,
                    },
                    "client-key": None if force_pairing else existing_key,
                },
            }
            request_material.extend(self._send(connection, registration))
            registration_response = self._receive_json(connection, timeout=10)
            response_material.extend(canonical_bytes(registration_response))
            if registration_response.get("type") == "response" and registration_response.get("payload", {}).get("pairingType") == "PROMPT":
                registration_response = self._receive_json(connection, timeout=approval_timeout)
                response_material.extend(canonical_bytes(registration_response))
            if registration_response.get("type") != "registered":
                raise PermissionError(
                    f"The television did not approve pairing: {registration_response.get('error', registration_response.get('type'))}"
                )
            client_key = str(registration_response.get("payload", {}).get("client-key") or existing_key or "")
            if not client_key:
                raise PermissionError("The television approved pairing without returning a client key")
            self._save_key(node_id, host, client_key)

            proof_request = {
                "id": "aion_read_volume",
                "type": "request",
                "uri": "ssap://audio/getVolume",
                "payload": {},
            }
            request_material.extend(self._send(connection, proof_request))
            proof_response = self._receive_json(connection, timeout=10)
            response_material.extend(canonical_bytes(proof_response))
            if proof_response.get("type") == "error" or not proof_response.get("payload", {}).get("returnValue"):
                raise PermissionError(
                    f"Pairing succeeded but the read-only volume proof was rejected: {proof_response.get('error', 'unknown response')}"
                )
            proof_payload = proof_response.get("payload", {})
            volume_status = proof_payload.get("volumeStatus", {})
            proof_values = {"returnValue": bool(proof_payload.get("returnValue"))}
            if "volume" in proof_payload or "volume" in volume_status:
                proof_values["volume"] = proof_payload.get("volume", volume_status.get("volume"))
            if "mute" in proof_payload or "mute" in volume_status:
                proof_values["muted"] = proof_payload.get("mute", volume_status.get("mute"))
            if "soundOutput" in proof_payload:
                proof_values["soundOutput"] = proof_payload["soundOutput"]
        return WebOsPairingReceipt(
            receipt_id=f"webos_pair_{uuid4().hex}",
            node_id=node_id,
            host=host,
            paired=True,
            reused_client_key=existing_key is not None,
            permissions_requested=list(PAIRING_PERMISSIONS),
            proof_action="ssap://audio/getVolume",
            proof_values=proof_values,
            request_hash=hashlib.sha256(request_material).hexdigest(),
            response_hash=hashlib.sha256(response_material).hexdigest(),
        )

    @staticmethod
    def _volume_from_payload(payload: Dict[str, Any]) -> int | None:
        volume_status = payload.get("volumeStatus", {})
        value = payload.get("volume", volume_status.get("volume"))
        return int(value) if isinstance(value, (int, float)) else None

    @staticmethod
    def netflix_profile_selection_buttons(profile_index: int) -> list[str]:
        if profile_index not in {1, 2, 3, 4, 5}:
            raise ValueError("Netflix profile position must be between one and five")
        return (["UP"] * 5) + (["DOWN"] * (profile_index - 1)) + ["ENTER"]

    @staticmethod
    def voice_volume_target(
        *, current: int, action: str, arguments: Dict[str, Any], maximum: int
    ) -> int:
        if action == "set_volume":
            requested = int(arguments["volume"])
            if requested > maximum:
                raise PermissionError(f"Voice volume is capped at {maximum}")
            return max(0, requested)
        delta = int(arguments["delta"])
        if delta > 0 and current >= maximum:
            raise PermissionError(
                f"The TV volume is already above AION's voice limit of {maximum}"
            )
        target = max(0, current + delta)
        return min(maximum, target) if delta > 0 else target

    def inventory_and_volume_round_trip(
        self,
        *,
        node_id: str,
        host: str,
    ) -> WebOsIntegrationReceipt:
        """Inventory proved SSAP surfaces and perform one verified reversible audio test."""
        host = self.validate_host(host)
        client_key = self._load_key(node_id, host)
        if not client_key:
            raise PermissionError("LG webOS pairing must be completed before integration")
        request_material = bytearray()
        response_material = bytearray()
        sequence = 0

        with self._connect(host) as connection:
            request_material.extend(self._send(connection, {"id": "hello", "type": "hello", "payload": {}}))
            response_material.extend(canonical_bytes(self._receive_json(connection, timeout=8)))
            preflight = {
                "id": "integration_preflight",
                "type": "request",
                "uri": "ssap://system/getSystemInfo",
                "payload": {},
            }
            request_material.extend(self._send(connection, preflight))
            response_material.extend(canonical_bytes(self._receive_json(connection, timeout=8)))
            registration = {
                "id": "register_aion_integration",
                "type": "register",
                "payload": {
                    "forcePairing": False,
                    "pairingType": "PROMPT",
                    "manifest": {
                        "manifestVersion": 1,
                        "appVersion": "0.47.0",
                        "permissions": PAIRING_PERMISSIONS,
                    },
                    "client-key": client_key,
                },
            }
            request_material.extend(self._send(connection, registration))
            registered = self._receive_json(connection, timeout=10)
            response_material.extend(canonical_bytes(registered))
            if registered.get("type") != "registered":
                raise PermissionError("The saved LG authorization is no longer accepted")

            def request(uri: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
                nonlocal sequence
                sequence += 1
                message = {
                    "id": f"aion_integration_{sequence}",
                    "type": "request",
                    "uri": f"ssap://{uri}",
                    "payload": payload or {},
                }
                request_material.extend(self._send(connection, message))
                response = self._receive_json(connection, timeout=12)
                response_material.extend(canonical_bytes(response))
                if response.get("type") == "error" or not response.get("payload", {}).get("returnValue"):
                    raise RuntimeError(str(response.get("error") or "request rejected"))
                return dict(response.get("payload", {}))

            endpoints = {
                "system": "system/getSystemInfo",
                "power": "com.webos.service.tvpower/power/getPowerState",
                "audio": "audio/getStatus",
                "volume": "audio/getVolume",
                "foreground_app": "com.webos.applicationManager/getForegroundAppInfo",
                "inputs": "tv/getExternalInputList",
                "launch_points": "com.webos.applicationManager/listLaunchPoints",
                "network": "com.webos.service.connectionmanager/getinfo",
                "services": "api/getServiceList",
            }
            results: Dict[str, Any] = {}
            errors: Dict[str, str] = {}
            for name, endpoint in endpoints.items():
                try:
                    results[name] = request(endpoint)
                except Exception as exc:
                    errors[name] = f"{type(exc).__name__}: {exc}"

            current_payload = results.get("volume") or request("audio/getVolume")
            original = self._volume_from_payload(current_payload)
            round_trip: Dict[str, Any] = {
                "attempted": False,
                "original": original,
                "target": None,
                "observed_target": None,
                "observed_restored": None,
                "restored": False,
            }
            if original is not None:
                target = original + 1 if original < 100 else original - 1
                round_trip.update({"attempted": True, "target": target})
                try:
                    request("audio/setVolume", {"volume": target})
                    round_trip["observed_target"] = self._volume_from_payload(request("audio/getVolume"))
                finally:
                    request("audio/setVolume", {"volume": original})
                    restored = self._volume_from_payload(request("audio/getVolume"))
                    round_trip["observed_restored"] = restored
                    round_trip["restored"] = restored == original
                if round_trip["observed_target"] != target or not round_trip["restored"]:
                    raise RuntimeError(f"LG volume round-trip verification failed: {round_trip}")

        return WebOsIntegrationReceipt(
            receipt_id=f"webos_integrate_{uuid4().hex}",
            node_id=node_id,
            host=host,
            connected_surfaces=sorted(results),
            read_results=results,
            read_errors=errors,
            volume_round_trip=round_trip,
            request_hash=hashlib.sha256(request_material).hexdigest(),
            response_hash=hashlib.sha256(response_material).hexdigest(),
        )
