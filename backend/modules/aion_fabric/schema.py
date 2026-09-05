from __future__ import annotations

import hashlib
import ipaddress
import json
import socket
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .canonical import canonical_hash, utc_now_iso
from .contracts import RiskLevel
from .discovery import DiscoveryObservation


@dataclass(slots=True)
class DocumentationArtifact:
    url: str
    local_path: str
    media_type: str
    size_bytes: int
    sha256: str
    acquired_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ControlSurface:
    action_id: str
    name: str
    protocol: str
    endpoint: str
    service_type: str
    risk: RiskLevel
    requires_approval: bool
    mode: str = "disabled_until_enrolled"
    arguments: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["risk"] = self.risk.value
        return value


@dataclass(slots=True)
class DeviceSchema:
    schema_id: str
    node_id: str
    manufacturer: str
    model_name: str
    model_number: str
    device_type: str
    friendly_name: str
    serial_number: str
    protocols: List[str]
    controls: List[ControlSurface]
    documentation: List[DocumentationArtifact]
    evidence: Dict[str, Any]
    confidence: float
    generated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "controls": [item.to_dict() for item in self.controls],
            "documentation": [item.to_dict() for item in self.documentation],
        }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        raise ValueError("Descriptor redirects are not allowed")


class SafeDescriptorFetcher:
    def __init__(self, output_dir: str | Path, *, max_bytes: int = 1024 * 1024) -> None:
        self.output_dir = Path(output_dir)
        self.max_bytes = max_bytes
        self.opener = urllib.request.build_opener(_NoRedirect())

    @staticmethod
    def _validate_url(url: str) -> urllib.parse.SplitResult:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Only HTTP(S) device descriptors are supported")
        if parsed.username or parsed.password:
            raise ValueError("Credential-bearing descriptor URLs are forbidden")
        default_port = 443 if parsed.scheme == "https" else 80
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or default_port)}
        if not addresses:
            raise ValueError("Descriptor host did not resolve")
        for address in addresses:
            ip = ipaddress.ip_address(address.split("%", 1)[0])
            if not (ip.is_private or ip.is_link_local or ip.is_loopback):
                raise ValueError("Automatic descriptor downloads are limited to the local network")
        return parsed

    def fetch(self, url: str, *, node_id: str, label: str) -> tuple[DocumentationArtifact, bytes]:
        self._validate_url(url)
        request = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": "AION-Device-Fabric/0.2 (descriptor-only)", "Accept": "application/xml, text/xml, application/json, text/plain"},
        )
        with self.opener.open(request, timeout=3) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > self.max_bytes:
                raise ValueError("Descriptor exceeds the configured size limit")
            payload = response.read(self.max_bytes + 1)
            if len(payload) > self.max_bytes:
                raise ValueError("Descriptor exceeds the configured size limit")
            media_type = response.headers.get_content_type()
        suffix = ".json" if "json" in media_type else ".xml" if "xml" in media_type else ".txt"
        digest = hashlib.sha256(payload).hexdigest()
        directory = self.output_dir / node_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{label}_{digest[:12]}{suffix}"
        path.write_bytes(payload)
        return (
            DocumentationArtifact(
                url=url,
                local_path=str(path),
                media_type=media_type,
                size_bytes=len(payload),
                sha256=digest,
            ),
            payload,
        )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first_text(root: ET.Element, name: str) -> str:
    for element in root.iter():
        if _local_name(element.tag) == name and element.text:
            return element.text.strip()
    return ""


def _risk_for_action(action: str) -> RiskLevel:
    value = action.lower()
    if value.startswith(("get", "query", "list", "read", "browse", "search")):
        return RiskLevel.LOW
    if any(term in value for term in ("factory", "reset", "delete", "install", "update", "purchase", "unlock", "reboot")):
        return RiskLevel.HIGH
    return RiskLevel.MEDIUM


class DeviceSchemaResolver:
    def __init__(self, documentation_dir: str | Path) -> None:
        self.fetcher = SafeDescriptorFetcher(documentation_dir)

    def resolve(self, node_id: str, observation: DiscoveryObservation) -> DeviceSchema:
        artifacts: List[DocumentationArtifact] = []
        controls: List[ControlSurface] = []
        values: Dict[str, str] = {}
        evidence: Dict[str, Any] = {"observation": observation.to_dict(), "errors": []}
        service_types = list(observation.attributes.get("service_types", []))
        sources = list(observation.attributes.get("sources", [observation.source]))
        protocols = list(dict.fromkeys([*sources, *service_types]))
        txt = observation.attributes.get("txt", {})
        if isinstance(txt, dict):
            values["manufacturer"] = str(txt.get("manufacturer", ""))
            values["modelName"] = str(txt.get("model", txt.get("md", "")))

        service_endpoints = observation.attributes.get("service_endpoints", {})

        def endpoint_for(service_type: str) -> str:
            value = service_endpoints.get(service_type, {}) if isinstance(service_endpoints, dict) else {}
            if value.get("target") and value.get("port"):
                return f"{value['target']}:{value['port']}"
            if observation.attributes.get("target") and observation.attributes.get("port"):
                return f"{observation.attributes['target']}:{observation.attributes['port']}"
            return ""

        if "_airplay._tcp" in service_types:
            for name in ("PrepareSession", "PlayMedia", "StopMedia", "SetVolume"):
                controls.append(
                    ControlSurface(
                        action_id=f"airplay.{name.lower()}",
                        name=name,
                        protocol="airplay",
                        endpoint=endpoint_for("_airplay._tcp"),
                        service_type="_airplay._tcp",
                        risk=RiskLevel.MEDIUM,
                        requires_approval=True,
                        mode="requires_pairing_and_adapter_validation",
                    )
                )
        if "_googlecast._tcp" in service_types:
            for name in ("ConnectSession", "LaunchReceiver", "LoadMedia", "StopMedia"):
                controls.append(
                    ControlSurface(
                        action_id=f"googlecast.{name.lower()}",
                        name=name,
                        protocol="googlecast",
                        endpoint=endpoint_for("_googlecast._tcp"),
                        service_type="_googlecast._tcp",
                        risk=RiskLevel.MEDIUM,
                        requires_approval=True,
                        mode="requires_pairing_and_adapter_validation",
                    )
                )

        if observation.descriptor_urls:
            services_all: List[Dict[str, str]] = []
            seen_urls: set[str] = set()
            for descriptor_index, descriptor_url in enumerate(observation.descriptor_urls[:8]):
                try:
                    artifact, payload = self.fetcher.fetch(
                        descriptor_url,
                        node_id=node_id,
                        label=f"device_{descriptor_index:02d}",
                    )
                    artifacts.append(artifact)
                    seen_urls.add(descriptor_url)
                    root = ET.fromstring(payload)
                    for name in ("manufacturer", "modelName", "modelNumber", "deviceType", "friendlyName", "serialNumber"):
                        found = _first_text(root, name)
                        if found:
                            values[name] = found
                    for service in root.iter():
                        if _local_name(service.tag) != "service":
                            continue
                        item = {_local_name(child.tag): (child.text or "").strip() for child in service}
                        if item.get("serviceType"):
                            item["descriptorBaseURL"] = descriptor_url
                            services_all.append(item)
                except Exception as exc:
                    evidence["errors"].append(
                        f"device descriptor {descriptor_index}: {type(exc).__name__}: {exc}"
                    )

            unique_services: Dict[tuple[str, str], Dict[str, str]] = {}
            for service in services_all:
                key = (service.get("serviceType", ""), service.get("controlURL", ""))
                unique_services[key] = service
            services = list(unique_services.values())
            evidence["services"] = services
            for index, service in enumerate(services[:32]):
                base_url = service.get("descriptorBaseURL", observation.descriptor_urls[0])
                scpd_url = urllib.parse.urljoin(base_url, service.get("SCPDURL", ""))
                control_url = urllib.parse.urljoin(base_url, service.get("controlURL", ""))
                if not scpd_url:
                    continue
                try:
                    if urllib.parse.urlsplit(scpd_url).hostname != urllib.parse.urlsplit(base_url).hostname:
                        raise ValueError("Service descriptor must remain on the advertised device host")
                    if scpd_url in seen_urls:
                        continue
                    scpd_artifact, scpd_payload = self.fetcher.fetch(
                        scpd_url, node_id=node_id, label=f"service_{index:02d}"
                    )
                    seen_urls.add(scpd_url)
                    artifacts.append(scpd_artifact)
                    scpd_root = ET.fromstring(scpd_payload)
                    for action in scpd_root.iter():
                        if _local_name(action.tag) != "action":
                            continue
                        action_name = _first_text(action, "name")
                        if not action_name:
                            continue
                        arguments = []
                        for argument in action.iter():
                            if _local_name(argument.tag) != "argument":
                                continue
                            arguments.append(
                                {
                                    "name": _first_text(argument, "name"),
                                    "direction": _first_text(argument, "direction"),
                                    "related_state_variable": _first_text(argument, "relatedStateVariable"),
                                }
                            )
                        risk = _risk_for_action(action_name)
                        controls.append(
                            ControlSurface(
                                action_id=f"upnp.{canonical_hash([service.get('serviceType'), action_name])[:18]}",
                                name=action_name,
                                protocol="upnp",
                                endpoint=control_url,
                                service_type=service.get("serviceType", ""),
                                risk=risk,
                                requires_approval=risk is not RiskLevel.LOW,
                                arguments=arguments,
                            )
                        )
                except Exception as exc:
                    evidence["errors"].append(f"service descriptor {index}: {type(exc).__name__}: {exc}")

        controls = list({control.action_id: control for control in controls}.values())

        friendly_name = values.get("friendlyName") or observation.name
        identity = {
            "node_id": node_id,
            "manufacturer": values.get("manufacturer", ""),
            "model": values.get("modelName", ""),
            "protocols": protocols,
            "controls": [control.action_id for control in controls],
        }
        confidence = min(0.98, observation.confidence + (0.15 if artifacts else 0) + (0.1 if controls else 0))
        return DeviceSchema(
            schema_id=f"schema_{canonical_hash(identity)[:24]}",
            node_id=node_id,
            manufacturer=values.get("manufacturer", ""),
            model_name=values.get("modelName", ""),
            model_number=values.get("modelNumber", ""),
            device_type=values.get("deviceType", observation.attributes.get("server", observation.source)),
            friendly_name=friendly_name,
            serial_number=values.get("serialNumber", ""),
            protocols=protocols,
            controls=controls,
            documentation=artifacts,
            evidence=evidence,
            confidence=confidence,
        )
