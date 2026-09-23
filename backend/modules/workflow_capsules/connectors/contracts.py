from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import time


CONNECTOR_CONTRACT_SCHEMA_VERSION = "aion.workflow_connector_contract.v1"


@dataclass
class ConnectorCapability:
    connector: str
    action: str
    live_supported: bool = False
    requires_vault: List[str] = field(default_factory=list)
    requires_approval: bool = False
    env_guards: List[str] = field(default_factory=list)

    schema_version: str = CONNECTOR_CONTRACT_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProviderConnectorResult:
    ok: bool
    connector: str
    action: str
    status: str

    payload: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    t: float = field(default_factory=time.time)

    schema_version: str = "aion.workflow_provider_connector_result.v1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProviderConnectorError(RuntimeError):
    pass
