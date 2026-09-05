from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from typing import Any, Dict
from uuid import uuid4
from xml.sax.saxutils import escape

from .canonical import canonical_hash, utc_now_iso
from .contracts import RiskLevel
from .schema import ControlSurface, SafeDescriptorFetcher, _NoRedirect, _local_name


class UpnpProbeRejected(RuntimeError):
    """A readable UPnP fault returned by a device for an observe-only action."""


@dataclass(slots=True)
class ReadOnlyProbeReceipt:
    receipt_id: str
    node_id: str
    action_id: str
    action_name: str
    protocol: str
    endpoint: str
    request_hash: str
    response_hash: str
    response_status: int
    values: Dict[str, Any]
    verified_read_only: bool
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def default_probe_arguments(control: ControlSurface) -> Dict[str, Any]:
    defaults: Dict[str, Any] = {}
    for argument in control.arguments:
        if str(argument.get("direction", "")).lower() != "in":
            continue
        name = str(argument.get("name", ""))
        normalized = name.lower()
        if normalized == "instanceid":
            defaults[name] = 0
        elif normalized == "channel":
            defaults[name] = "Master"
        elif normalized in {"objectid", "containerid"}:
            defaults[name] = "0"
        elif normalized in {"startingindex", "requestedcount"}:
            defaults[name] = 0
        elif normalized == "browseflag":
            defaults[name] = "BrowseMetadata"
        elif normalized == "filter":
            defaults[name] = "*"
        elif normalized == "sortcriteria":
            defaults[name] = ""
        else:
            raise ValueError(f"No safe default is known for required argument {name!r}")
    return defaults


class UpnpReadOnlyProbeAdapter:
    MAX_RESPONSE_BYTES = 1024 * 1024

    def execute(
        self,
        *,
        node_id: str,
        control: ControlSurface,
        arguments: Dict[str, Any],
    ) -> ReadOnlyProbeReceipt:
        if control.protocol != "upnp" or control.risk is not RiskLevel.LOW:
            raise PermissionError("The preview adapter accepts only evidenced low-risk UPnP queries")
        if not control.name.lower().startswith(("get", "query", "list", "read", "browse", "search")):
            raise PermissionError("The proposed action is not classified as read-only")
        SafeDescriptorFetcher._validate_url(control.endpoint)
        supplied = dict(arguments)
        expected_inputs = {
            str(argument.get("name"))
            for argument in control.arguments
            if str(argument.get("direction", "")).lower() == "in"
        }
        if set(supplied) != expected_inputs:
            raise ValueError(
                f"Probe arguments must exactly match the evidenced inputs: {sorted(expected_inputs)}"
            )
        body_arguments = "".join(
            f"<{escape(name)}>{escape(str(value))}</{escape(name)}>"
            for name, value in supplied.items()
        )
        body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            f'<s:Body><u:{escape(control.name)} xmlns:u="{escape(control.service_type)}">'
            f"{body_arguments}</u:{escape(control.name)}></s:Body></s:Envelope>"
        ).encode("utf-8")
        request = urllib.request.Request(
            control.endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": 'text/xml; charset="utf-8"',
                "SOAPAction": f'"{control.service_type}#{control.name}"',
                "User-Agent": "AION-Device-Fabric/0.2 (read-only-probe)",
            },
        )
        opener = urllib.request.build_opener(_NoRedirect())
        try:
            with opener.open(request, timeout=4) as response:
                payload = response.read(self.MAX_RESPONSE_BYTES + 1)
                if len(payload) > self.MAX_RESPONSE_BYTES:
                    raise ValueError("Probe response exceeds the configured size limit")
                status = int(getattr(response, "status", 200))
        except urllib.error.HTTPError as exc:
            payload = exc.read(self.MAX_RESPONSE_BYTES + 1)
            error_code = ""
            description = ""
            try:
                fault_root = ET.fromstring(payload)
                for element in fault_root.iter():
                    name = _local_name(element.tag)
                    if name == "errorCode" and element.text:
                        error_code = element.text.strip()
                    elif name == "errorDescription" and element.text:
                        description = element.text.strip()
            except ET.ParseError:
                pass
            detail = description or exc.reason or "request rejected"
            code = f"UPnP {error_code}, " if error_code else ""
            raise UpnpProbeRejected(
                f"Device rejected {control.name}: {detail} ({code}HTTP {exc.code})"
            ) from exc
        root = ET.fromstring(payload)
        values: Dict[str, Any] = {}
        for element in root.iter():
            if len(element) == 0 and element.text is not None:
                key = _local_name(element.tag)
                if key not in {"Envelope", "Body", f"{control.name}Response"}:
                    values[key] = element.text.strip()
        return ReadOnlyProbeReceipt(
            receipt_id=f"probe_{uuid4().hex}",
            node_id=node_id,
            action_id=control.action_id,
            action_name=control.name,
            protocol=control.protocol,
            endpoint=control.endpoint,
            request_hash=hashlib.sha256(body).hexdigest(),
            response_hash=hashlib.sha256(payload).hexdigest(),
            response_status=status,
            values=values,
            verified_read_only=True,
        )
