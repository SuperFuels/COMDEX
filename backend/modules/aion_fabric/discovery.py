from __future__ import annotations

import hashlib
import json
import re
import signal
import shlex
import socket
import subprocess
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List

from .canonical import canonical_hash, utc_now_iso
from .contracts import DeviceProfile


@dataclass(slots=True)
class DiscoveryObservation:
    observation_id: str
    source: str
    name: str
    addresses: List[str]
    identifiers: Dict[str, str]
    attributes: Dict[str, Any]
    descriptor_urls: List[str] = field(default_factory=list)
    observed_at: str = field(default_factory=utc_now_iso)
    confidence: float = 0.4

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def stable_key(self) -> str:
        candidates = [
            self.identifiers.get("usn"),
            self.identifiers.get("mac"),
            next(iter(self.addresses), None),
            self.identifiers.get("service_instance"),
            self.name,
        ]
        return next((str(value).lower() for value in candidates if value), self.observation_id)


@dataclass(slots=True)
class DiscoveryRun:
    run_id: str
    started_at: str
    completed_at: str
    mode: str
    observations: List[DiscoveryObservation]
    errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "mode": self.mode,
            "observations": [item.to_dict() for item in self.observations],
            "errors": self.errors,
        }


def _observation_id(source: str, identity: Dict[str, Any]) -> str:
    return f"obs_{source}_{canonical_hash(identity)[:20]}"


def _classify(text: str) -> str:
    value = text.lower()
    classes = (
        ("television", ("tv", "television", "airplay", "tizen", "webos", "roku", "chromecast")),
        ("printer", ("printer", "ipp", "scanner")),
        ("speaker", ("speaker", "audio", "sonos", "raop")),
        ("router", ("router", "gateway", "internetgatewaydevice")),
        ("camera", ("camera", "onvif", "doorbell")),
        ("light", ("light", "hue", "lamp")),
        ("appliance", ("fridge", "refrigerator", "washer", "dryer", "oven", "appliance")),
        ("computer", ("macbook", "laptop", "computer", "workstation")),
        ("phone", ("iphone", "android", "phone")),
    )
    return next((kind for kind, terms in classes if any(term in value for term in terms)), "unknown")


def profile_from_observation(observation: DiscoveryObservation) -> DeviceProfile:
    combined = " ".join(
        [observation.name, observation.source]
        + [str(value) for value in observation.attributes.values()]
        + [str(value) for value in observation.identifiers.values()]
    )
    node_id = f"node_discovered_{hashlib.sha256(observation.stable_key.encode()).hexdigest()[:16]}"
    transports = {
        "ssdp": "wifi",
        "bonjour": "wifi",
        "arp": "network",
        "bluetooth": "ble",
    }
    txt = observation.attributes.get("txt", {})
    identity_aliases: set[str] = set()
    for key in ("mac", "bluetooth_address"):
        value = observation.identifiers.get(key)
        if value:
            identity_aliases.add(f"{key}:{str(value).strip().lower()}")
    usn = observation.identifiers.get("usn", "")
    if usn:
        identity_aliases.add(f"usn_uuid:{str(usn).split('::', 1)[0].strip().lower()}")
    if isinstance(txt, dict):
        for key in ("id", "deviceid"):
            value = txt.get(key)
            if value:
                identity_aliases.add(f"advertised_{key}:{str(value).strip().lower()}")
    for address in observation.addresses:
        if address:
            identity_aliases.add(f"address:{str(address).split('%', 1)[0].strip().lower()}")
    advertised_platform = " ".join(
        str(value) for value in (txt.get("manufacturer", ""), txt.get("model", txt.get("md", ""))) if value
    ) if isinstance(txt, dict) else ""
    return DeviceProfile(
        node_id=node_id,
        name=observation.name or "Unidentified device",
        device_class=_classify(combined),
        platform=advertised_platform or observation.attributes.get("server", observation.source),
        cpu_count=0,
        memory_bytes=0,
        can_install_runtime=False,
        can_host_model=False,
        is_mains_powered=False,
        transports=(transports.get(observation.source, observation.source),),
        controls=(),
        metadata={
            "discovery_source": observation.source,
            "observation_id": observation.observation_id,
            "addresses": observation.addresses,
            "identifiers": observation.identifiers,
            "attributes": observation.attributes,
            "descriptor_urls": observation.descriptor_urls,
            "confidence": observation.confidence,
            "identity_aliases": sorted(identity_aliases),
        },
    )


class SafeDiscoveryEngine:
    """Bounded discovery using advertised data and the existing neighbor cache."""

    COMMON_BONJOUR_TYPES = (
        "_airplay._tcp",
        "_googlecast._tcp",
        "_hap._tcp",
        "_ipp._tcp",
        "_raop._tcp",
        "_http._tcp",
        "_companion-link._tcp",
        "_matter._tcp",
    )

    def scan(self, timeout_seconds: float = 2.5) -> DiscoveryRun:
        timeout_seconds = max(0.5, min(float(timeout_seconds), 8.0))
        started = utc_now_iso()
        errors: List[str] = []
        observations: List[DiscoveryObservation] = []
        collectors = (
            ("arp", lambda: self._arp_neighbors()),
            ("ssdp", lambda: self._ssdp(timeout_seconds=min(timeout_seconds, 3.0))),
            ("bonjour", lambda: self._bonjour(timeout_seconds=min(timeout_seconds, 2.0))),
            ("bluetooth", lambda: self._known_bluetooth()),
        )
        for name, collector in collectors:
            try:
                observations.extend(collector())
            except Exception as exc:
                errors.append(f"{name}: {type(exc).__name__}: {exc}")
        merged = self._merge(observations)
        return DiscoveryRun(
            run_id=f"discovery_{int(time.time() * 1000)}",
            started_at=started,
            completed_at=utc_now_iso(),
            mode="safe_advertised_and_neighbor_cache",
            observations=merged,
            errors=errors,
        )

    def _arp_neighbors(self) -> List[DiscoveryObservation]:
        result = subprocess.run(
            ["/usr/sbin/arp", "-an"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        observations: List[DiscoveryObservation] = []
        pattern = re.compile(r"^\? \(([^)]+)\) at ([0-9a-f:]+) on ([^ ]+)", re.I)
        for line in result.stdout.splitlines():
            match = pattern.match(line.strip())
            if not match:
                continue
            address, mac, interface = match.groups()
            if mac.lower() == "ff:ff:ff:ff:ff:ff" or address.startswith(("224.", "239.")):
                continue
            identity = {"mac": mac.lower(), "address": address}
            observations.append(
                DiscoveryObservation(
                    observation_id=_observation_id("arp", identity),
                    source="arp",
                    name=f"Network device {address}",
                    addresses=[address],
                    identifiers={"mac": mac.lower()},
                    attributes={"interface": interface, "evidence": "existing_neighbor_cache"},
                    confidence=0.3,
                )
            )
        return observations

    def _ssdp(self, timeout_seconds: float) -> List[DiscoveryObservation]:
        message = (
            "M-SEARCH * HTTP/1.1\r\n"
            "HOST: 239.255.255.250:1900\r\n"
            'MAN: "ssdp:discover"\r\n'
            "MX: 1\r\n"
            "ST: ssdp:all\r\n\r\n"
        ).encode("ascii")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.settimeout(0.2)
        observations: List[DiscoveryObservation] = []
        deadline = time.monotonic() + timeout_seconds
        try:
            sock.sendto(message, ("239.255.255.250", 1900))
            while time.monotonic() < deadline:
                try:
                    payload, sender = sock.recvfrom(64 * 1024)
                except TimeoutError:
                    continue
                text = payload.decode("utf-8", errors="replace")
                headers: Dict[str, str] = {}
                for line in text.replace("\r\n", "\n").split("\n")[1:]:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        headers[key.strip().lower()] = value.strip()
                usn = headers.get("usn", f"{sender[0]}:{sender[1]}")
                location = headers.get("location")
                server = headers.get("server", "SSDP device")
                observations.append(
                    DiscoveryObservation(
                        observation_id=_observation_id("ssdp", {"usn": usn}),
                        source="ssdp",
                        name=headers.get("friendlyname", server.split("/")[0].strip() or "SSDP device"),
                        addresses=[sender[0]],
                        identifiers={"usn": usn, "service_type": headers.get("st", "")},
                        attributes={"server": server, "cache_control": headers.get("cache-control", "")},
                        descriptor_urls=[location] if location else [],
                        confidence=0.75,
                    )
                )
        finally:
            sock.close()
        return observations

    def _bonjour(self, timeout_seconds: float) -> List[DiscoveryObservation]:
        observations: List[DiscoveryObservation] = []
        per_type = max(0.15, timeout_seconds / len(self.COMMON_BONJOUR_TYPES))
        processes: List[tuple[str, subprocess.Popen[str]]] = []
        for service_type in self.COMMON_BONJOUR_TYPES:
            process = subprocess.Popen(
                ["/usr/bin/dns-sd", "-B", service_type, "local."],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            processes.append((service_type, process))
        time.sleep(min(timeout_seconds, 2.0))
        for service_type, process in processes:
            process.send_signal(signal.SIGINT)
            try:
                output, _ = process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                output, _ = process.communicate(timeout=1)
            for line in output.splitlines():
                if " Add " not in line or " local." not in line:
                    continue
                match = re.search(r"\s+local\.\s+\S+\s+(.+)$", line)
                instance = match.group(1).strip() if match else ""
                if not instance:
                    continue
                addresses, resolved = self._resolve_bonjour(instance, service_type)
                identity = {"service_type": service_type, "instance": instance}
                observations.append(
                    DiscoveryObservation(
                        observation_id=_observation_id("bonjour", identity),
                        source="bonjour",
                        name=instance,
                        addresses=addresses,
                        identifiers={"service_type": service_type, "service_instance": instance},
                        attributes={
                            "domain": "local.",
                            "service_types": [service_type],
                            "service_endpoints": {
                                service_type: {
                                    "target": resolved.get("target", ""),
                                    "port": resolved.get("port", 0),
                                }
                            },
                            **resolved,
                        },
                        confidence=0.75 if addresses else 0.65,
                    )
                )
        return observations

    def _resolve_bonjour(self, instance: str, service_type: str) -> tuple[List[str], Dict[str, Any]]:
        process = subprocess.Popen(
            ["/usr/bin/dns-sd", "-L", instance, service_type, "local."],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        time.sleep(0.75)
        process.send_signal(signal.SIGINT)
        try:
            output, _ = process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate(timeout=1)
        target_match = re.search(r"can be reached at (\S+):(\d+)", output)
        if not target_match:
            return [], {}
        target, port_text = target_match.groups()
        target = target.rstrip(".")
        port = int(port_text)
        addresses: List[str] = []
        try:
            addresses = sorted({item[4][0].split("%", 1)[0] for item in socket.getaddrinfo(target, port)})
        except OSError:
            pass
        txt: Dict[str, str] = {}
        lines = output.splitlines()
        reached_index = next((index for index, line in enumerate(lines) if "can be reached at" in line), -1)
        if reached_index >= 0 and reached_index + 1 < len(lines):
            try:
                for token in shlex.split(lines[reached_index + 1].strip()):
                    if "=" in token:
                        key, value = token.split("=", 1)
                        if key in {"model", "md", "manufacturer", "fn", "deviceid", "id", "srcvers", "protovers"}:
                            txt[key] = value.replace("\\ ", " ").replace("\\[", "[").replace("\\]", "]")
            except ValueError:
                pass
        return addresses, {"target": target, "port": port, "txt": txt}

    def _known_bluetooth(self) -> List[DiscoveryObservation]:
        result = subprocess.run(
            ["/usr/sbin/system_profiler", "SPBluetoothDataType", "-json"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if not result.stdout.strip():
            return []
        data = json.loads(result.stdout)
        found: List[DiscoveryObservation] = []

        def walk(value: Any, label: str = "") -> None:
            if isinstance(value, dict):
                address = next(
                    (str(item) for key, item in value.items() if "address" in key.lower() and isinstance(item, str) and ":" in item),
                    None,
                )
                if address:
                    name = str(value.get("device_name") or value.get("_name") or label or "Bluetooth device")
                    if "controller" in name.lower():
                        for key, item in value.items():
                            walk(item, str(key))
                        return
                    identity = {"address": address.lower()}
                    found.append(
                        DiscoveryObservation(
                            observation_id=_observation_id("bluetooth", identity),
                            source="bluetooth",
                            name=name,
                            addresses=[],
                            identifiers={"bluetooth_address": address.lower()},
                            attributes={"evidence": "macos_known_bluetooth"},
                            confidence=0.55,
                        )
                    )
                for key, item in value.items():
                    walk(item, str(key))
            elif isinstance(value, list):
                for item in value:
                    walk(item, label)

        walk(data)
        return found

    @staticmethod
    def _merge(observations: Iterable[DiscoveryObservation]) -> List[DiscoveryObservation]:
        def model_tokens(item: DiscoveryObservation) -> set[str]:
            text = " ".join(
                [item.name]
                + [str(value) for value in item.attributes.get("txt", {}).values()]
            ).upper()
            return {token for token in re.findall(r"[A-Z0-9]{8,}", text) if not token.isdigit()}

        def likely_same_advertised_device(left: DiscoveryObservation, right: DiscoveryObservation) -> bool:
            if left.source != "bonjour" or right.source != "bonjour":
                return False
            left_tokens, right_tokens = model_tokens(left), model_tokens(right)
            return any(
                left_token in right_token or right_token in left_token
                for left_token in left_tokens
                for right_token in right_tokens
            )

        merged: List[DiscoveryObservation] = []
        ordered = sorted(observations, key=lambda item: (-item.confidence, item.source, item.name.lower()))
        for observation in ordered:
            address_set = set(observation.addresses)
            current = next(
                (
                    item
                    for item in merged
                    if item.stable_key == observation.stable_key
                    or (address_set and address_set.intersection(item.addresses))
                    or likely_same_advertised_device(item, observation)
                ),
                None,
            )
            if current is None:
                observation.attributes.setdefault("sources", [observation.source])
                merged.append(observation)
                continue
            current.addresses = sorted(set(current.addresses + observation.addresses))
            current.descriptor_urls = sorted(set(current.descriptor_urls + observation.descriptor_urls))
            current.identifiers.update({key: value for key, value in observation.identifiers.items() if value})
            existing_service_types = set(current.attributes.get("service_types", []))
            existing_sources = set(current.attributes.get("sources", [current.source]))
            existing_txt = dict(current.attributes.get("txt", {}))
            existing_endpoints = dict(current.attributes.get("service_endpoints", {}))
            current.attributes.update(observation.attributes)
            service_types = existing_service_types | set(current.attributes.get("service_types", []))
            service_types.update(observation.attributes.get("service_types", []))
            if current.identifiers.get("service_type"):
                service_types.add(current.identifiers["service_type"])
            if observation.identifiers.get("service_type"):
                service_types.add(observation.identifiers["service_type"])
            if service_types:
                current.attributes["service_types"] = sorted(service_types)
            existing_sources.update(observation.attributes.get("sources", [observation.source]))
            current.attributes["sources"] = sorted(existing_sources)
            existing_txt.update({key: value for key, value in observation.attributes.get("txt", {}).items() if value})
            if existing_txt:
                current.attributes["txt"] = existing_txt
            existing_endpoints.update(observation.attributes.get("service_endpoints", {}))
            if existing_endpoints:
                current.attributes["service_endpoints"] = existing_endpoints
            current.confidence = max(current.confidence, observation.confidence)
        return sorted(merged, key=lambda item: (item.source, item.name.lower(), item.observation_id))
