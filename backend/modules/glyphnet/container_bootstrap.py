# backend/modules/glyphnet/container_bootstrap.py

"""
ContainerBootstrap: Handles booting or resuming symbolic containers.
Used during teleportation or glyph execution dispatch.
"""

from backend.modules.runtime.container_runtime import ContainerRuntime
from backend.modules.consciousness.state_manager import STATE


class ContainerBootstrap:
    def __init__(self):
        self.runtime = ContainerRuntime(state_manager=STATE)

    def resume_or_boot(self, container_id: str):
        """
        Attempt to resume a container by ID. If not found, try cold boot.
        """
        container = self.runtime.get_active_container(container_id)
        if container:
            return container

        # Attempt cold boot
        return self.runtime.boot_container(container_id)