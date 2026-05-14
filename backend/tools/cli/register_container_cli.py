# 📄 backend/tools/cli/register_container_cli.py

import sys
import logging
import os

from backend.modules.dimensions.containers.container_loader import load_container_from_file
from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime
from backend.modules.sqi.sqi_container_registry import _registry_register

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("register_container_cli")


def main():
    if len(sys.argv) < 2:
        print("Usage: python backend/tools/cli/register_container_cli.py <container_id>")
        sys.exit(1)

    container_id = sys.argv[1]
    if not container_id.endswith(".dc.json"):
        container_id += ".dc.json"

    container_path = f"backend/modules/dimensions/containers/{container_id}"

    if not os.path.exists(container_path):
        log.error(f"❌ Container file not found: {container_path}")
        sys.exit(1)

    log.info(f"🔍 Loading container from file: {container_path}")

    try:
        container = load_container_from_file(container_path)
        get_ucs_runtime().register(container)
        _registry_register(container_id.replace(".dc.json", ""), "ucs://knowledge")

        log.info(f"✅ Registered container '{container_id}' into UCS runtime and symbolic registry.")
        sys.exit(0)
    except Exception as e:
        log.error(f"❌ Failed to register container '{container_id}': {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()