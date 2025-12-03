# backend/devtools/smoke_holo_export.py

from backend.modules.runtime.container_runtime import get_container_runtime
from backend.modules.holo.holo_service import export_holo_from_container

# TODO: change this to an actual container id you know exists
CONTAINER_ID = "dc_aion_core"


def main():
    cr = get_container_runtime()

    # Load + activate the container into the runtime
    container = cr.load_and_activate_container(CONTAINER_ID)
    print(f"Loaded container: {container.get('id')}")

    # Use whatever view_ctx you like for the snapshot
    view_ctx = {
        "tick": getattr(cr, "tick_counter", 0),
        "reason": "smoke_test",
        "source_view": "qfc",
        "frame": "mutated",
        "tags": ["smoke-test"],
    }

    holo = export_holo_from_container(container, view_ctx, revision=1)

    print("Holo snapshot created:")
    print("  holo_id:", holo.holo_id)
    print("  container_id:", holo.container_id)


if __name__ == "__main__":
    main()