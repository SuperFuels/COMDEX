import sys
import json
import os
from rich import print
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.dimensions.universal_container_system.ucs_runtime import get_ucs_runtime
from backend.modules.dimensions.universal_container_system.ucs_runtime import UCSRuntime

def container_to_dict(container):
    """
    Normalize any container (UCSBaseContainer or dict) to a plain dict for Knowledge Graph.
    """
    if isinstance(container, dict):
        return container
    elif hasattr(container, "to_dict"):
        return container.to_dict()
    elif hasattr(container, "payload"):
        return container.payload
    else:
        # Fallback: extract common fields manually
        return {
            "id": getattr(container, "id", None),
            "title": getattr(container, "title", None),
            "type": getattr(container, "type", None),
            "glyphs": getattr(container, "glyphs", []),
            "entropy": getattr(container, "entropy", None),
        }

def register_container(container_path: str):
    UCSRuntime.load_container(container_path)
    cid = container_path.replace(".dc.json", "").split("/")[-1]
    container = UCSRuntime.get_container(cid)

    # ✅ Handle both UCSBaseContainer (has .id) and dict (has ['id'])
    container_id = getattr(container, "id", None) or (
        container.get("id") if isinstance(container, dict) else None
    ) or os.path.splitext(os.path.basename(container_path))[0]

    # Register in UCS Runtime
    ucs_runtime = get_ucs_runtime()
    ucs_runtime.register_container(container_id, container)

    # Register in Knowledge Graph
    kg_writer = get_kg_writer()
    if kg_writer:
        data = container_to_dict(container)
        kg_writer.attach_container(data)
        print(f"[green]✅ Registered container '{container_id}' → KG + UCS runtime.[/green]")
    else:
        print(f"[yellow]⚠️ No KnowledgeGraphWriter available. UCS-only registration complete.[/yellow]")

def show_info(container_path: str):
    UCSRuntime.load_container(container_path)
    cid = container_path.replace(".dc.json", "").split("/")[-1]
    container = UCSRuntime.get_container(cid)

    # 🧠 Extract info safely from either dict or UCSBaseContainer
    get = container.get if isinstance(container, dict) else lambda k, d=None: getattr(container, k, d)

    print(f"\n📦 [bold]Container Info:[/bold]")
    print(f"  └─ ID:      {get('id', 'n/a')}")
    print(f"  └─ Title:   {get('title', 'n/a')}")
    print(f"  └─ Type:    {get('type', 'n/a')}")
    print(f"  └─ Glyphs:  {len(get('glyphs', []))}")
    print(f"  └─ Entropy: {get('entropy', 'n/a')}\n")

def print_json(container_path: str):
    try:
        with open(container_path, "r") as f:
            data = json.load(f)
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"[red]❌ Failed to load JSON: {e}[/red]")

def main():
    if len(sys.argv) < 3:
        print("[cyan]Usage:[/cyan] python backend/tools/container_loader_cli.py [register|info|print] path/to/container.dc.json")
        return

    command = sys.argv[1]
    container_path = sys.argv[2]

    if not os.path.exists(container_path):
        print(f"[red]❌ File not found:[/red] {container_path}")
        return

    try:
        if command == "register":
            register_container(container_path)
        elif command == "info":
            show_info(container_path)
        elif command == "print":
            print_json(container_path)
        else:
            print(f"[red]❌ Unknown command:[/red] {command}")
    except Exception as e:
        print(f"[red]❌ Error while executing '{command}': {e}[/red]")

if __name__ == "__main__":
    main()