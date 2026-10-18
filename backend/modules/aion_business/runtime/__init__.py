"""Runtime exports loaded on demand to keep utility imports side-effect free."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .container_adapter import BusinessContainerAdapter
    from .container_binding_repository import ContainerBindingRepository
    from .kg_adapter import BusinessKGAdapter
    from .role_binding_resolver import RoleBindingResolver
    from .role_runtime import RoleRuntime
    from .workspace_repository import WorkspaceRepository


_LAZY_EXPORTS = {
    "WorkspaceRepository": ("workspace_repository", "WorkspaceRepository"),
    "ContainerBindingRepository": ("container_binding_repository", "ContainerBindingRepository"),
    "BusinessContainerAdapter": ("container_adapter", "BusinessContainerAdapter"),
    "BusinessKGAdapter": ("kg_adapter", "BusinessKGAdapter"),
    "RoleBindingResolver": ("role_binding_resolver", "RoleBindingResolver"),
    "RoleRuntime": ("role_runtime", "RoleRuntime"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = target
    value = getattr(import_module(f"{__name__}.{module_name}"), attribute_name)
    globals()[name] = value
    return value

__all__ = [
    "WorkspaceRepository",
    "BusinessContainerAdapter",
    "BusinessKGAdapter",
]
