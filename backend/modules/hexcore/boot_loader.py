import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.knowledge_graph.knowledge_graph_writer import kg_writer
from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# Paths
BASE_DIR = os.path.dirname(__file__)
BOOTLOADER_FILE = os.path.join(BASE_DIR, "matrix_bootloader.json")
MEMORY_FILE = os.path.join(BASE_DIR, "aion_memory.json")

# --- NEW: Domain seed & save locations (multiple candidates; first that exists wins) ---
# We try to read seeds from these; we persist into SAVE_DIR.
REPO_ROOT = Path(BASE_DIR).resolve().parents[3] if len(Path(BASE_DIR).resolve().parents) >= 4 else Path(BASE_DIR).resolve().parents[-1]
DOMAIN_SEED_DIRS = [
    REPO_ROOT / "backend" / "modules" / "dimensions" / "containers",                          # e.g. backend/modules/dimensions/containers/*.dc.json
    REPO_ROOT / "backend" / "modules" / "dimensions" / "ucs" / "containers",                  # alt location
    REPO_ROOT / "backend" / "modules" / "dimensions" / "universal_container_system" / "seeds" # alt location
]
DOMAIN_SAVE_DIR = REPO_ROOT / "backend" / "modules" / "dimensions" / "containers_saved"
DOMAIN_SAVE_DIR.mkdir(parents=True, exist_ok=True)

# Loaders & Savers
def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        return json.load(f)

def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def dependencies_met(skill, memory_data):
    """Check if all dependencies are learned."""
    learned_titles = {entry["title"] for entry in memory_data if entry.get("status") == "learned"}
    for dep in skill.get("dependencies", []):
        if dep not in learned_titles:
            return False
    return True

# Enhanced Bootloader core
def load_boot_goals():
    boot_skills = load_json(BOOTLOADER_FILE)
    memory_data = load_json(MEMORY_FILE)

    memory_titles = {entry["title"] for entry in memory_data}
    tracker = MilestoneTracker()
    updated_memory = memory_data.copy()
    new_entries = []
    promoted_count = 0

    # Add new skills from bootloader file if missing
    for skill in boot_skills:
        title = skill.get("title")
        tags = skill.get("tags", [])
        if title not in memory_titles:
            milestone_ready = tracker.is_milestone_triggered(tags)
            # If milestone triggered AND dependencies met, mark 'ready' else 'queued'
            status = "ready" if milestone_ready else "queued"
            skill_entry = {
                "title": title,
                "tags": tags,
                "description": skill.get("description", ""),
                "status": status,
                "source": "bootloader",
                "added_on": datetime.utcnow().isoformat(),
                "priority": skill.get("priority", 1),
                "dependencies": skill.get("dependencies", []),
                "learned_on": None
            }
            new_entries.append(skill_entry)

    if new_entries:
        updated_memory.extend(new_entries)
        print(f"✅ {len(new_entries)} new skills added to memory.")

    # Promote 'ready' skills to 'queued' if dependencies met
    for entry in updated_memory:
        if entry.get("status") == "ready":
            if dependencies_met(entry, updated_memory):
                entry["status"] = "queued"
                promoted_count += 1

    if promoted_count > 0:
        print(f"⬆️ Promoted {promoted_count} skills from 'ready' to 'queued' based on dependencies.")

    # Save updated memory (persist across restarts)
    save_json(MEMORY_FILE, updated_memory)

    if not new_entries and promoted_count == 0:
        print("ℹ️ No new bootloader skills added or promoted. Memory is up to date.")

# ─────────────────────────────────────────────────────────────────────────────
# KG domain pack loader: push physics_core seed into the Knowledge Graph
# ─────────────────────────────────────────────────────────────────────────────
def load_domain_packs_into_kg():
    """
    Pull domain containers from UCS and write them into the Knowledge Graph.
    Currently handles physics_core. Safe to call even if container isn't loaded.
    """
    try:
        container = ucs_runtime.get_container("physics_core")
        if container and container.get("nodes"):
            # Prefer to attach so glyphs land in the same container space
            try:
                kg_writer.attach_container(container)  # added in KG writer
            except Exception:
                pass
            loaded = kg_writer.load_domain_pack("physics_core", container)
            if loaded:
                print("🧠 KG: physics_core domain loaded into Knowledge Graph.")
            else:
                print("ℹ️ KG: physics_core load_domain_pack returned False (not handled).")
        else:
            print("ℹ️ KG: physics_core not present in UCS yet; skipping KG load.")
    except Exception as e:
        print(f"⚠️ KG domain load skipped: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# NEW: Persistence helpers — ensure domain packs survive restarts
# ─────────────────────────────────────────────────────────────────────────────
def _resolve_dc_seed_path(container_id: str) -> Optional[Path]:
    """Find a seed .dc.json for a given container id, searching known seed dirs."""
    filename = f"{container_id}.dc.json"
    for d in DOMAIN_SEED_DIRS:
        p = (d / filename)
        if p.exists():
            return p
    return None

def _get_saved_dc_path(container_id: str) -> Path:
    """Where we persist domain packs we’ve loaded."""
    return DOMAIN_SAVE_DIR / f"{container_id}.dc.json"

def save_domain_pack_to_disk(container: Dict[str, Any]) -> Optional[Path]:
    """Persist a container dict to disk so it’s available at next boot."""
    if not container or not isinstance(container, dict):
        return None
    cid = container.get("id") or container.get("name")
    if not cid:
        return None
    path = _get_saved_dc_path(cid)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(container, f, indent=2)
        print(f"💾 Saved domain pack to {path}")
        return path
    except Exception as e:
        print(f"⚠️ Failed to save domain pack {cid}: {e}")
        return None

def load_container_from_disk(container_id: str) -> Optional[Dict[str, Any]]:
    """
    Try to load a domain container from disk (saved), falling back to seed file.
    If found, registers it into UCS (no-op if already present).
    """
    # Prefer previously saved snapshot
    saved = _get_saved_dc_path(container_id)
    seed = _resolve_dc_seed_path(container_id)
    picked: Optional[Path] = None

    if saved.exists():
        picked = saved
    elif seed is not None:
        picked = seed

    if not picked:
        return None

    # If UCS doesn't have it, load it now
    existing = ucs_runtime.get_container(container_id)
    if not existing or not existing.get("id"):
        try:
            # ucs_runtime.load_container expects a path to .dc.json
            name = ucs_runtime.load_container(str(picked))
            print(f"📦 Loaded '{name}' container from {picked}")
        except Exception as e:
            print(f"⚠️ Failed to load container {container_id} from {picked}: {e}")

    return ucs_runtime.get_container(container_id)

def preload_and_persist_domain_pack(container_id: str) -> bool:
    """
    Ensure a domain pack is:
      1) available in UCS (load from disk/seed if missing)
      2) persisted to disk under containers_saved/
      3) written into KG so nodes/edges influence reasoning
    Returns True if a pack was handled.
    """
    # 1) Ensure it's in UCS
    container = ucs_runtime.get_container(container_id)
    if not container or not container.get("nodes"):
        container = load_container_from_disk(container_id)

    if not container or not container.get("nodes"):
        print(f"ℹ️ Domain '{container_id}' not found on disk or seed; skipping.")
        return False

    # 2) Persist to disk (snap current UCS state)
    save_domain_pack_to_disk(container)

    # 3) Push into KG
    try:
        # Attach so glyphs land in this container’s space when possible
        try:
            kg_writer.attach_container(container)
        except Exception:
            pass
        handled = kg_writer.load_domain_pack(container_id, container)
        if handled:
            print(f"🧠 KG: {container_id} nodes/edges injected.")
        else:
            print(f"ℹ️ KG: {container_id} not handled by load_domain_pack.")
        return handled
    except Exception as e:
        print(f"⚠️ KG injection failed for {container_id}: {e}")
        return False

def preload_all_domain_packs():
    """
    One-stop boot: make sure all packs we care about are loaded and persisted.
    Extend this list as you add more packs.
    """
    targets = [
        "physics_core",
        # "math_core",
        # "control_systems",
        # add more here as they’re ready
    ]
    any_handled = False
    for cid in targets:
        handled = preload_and_persist_domain_pack(cid)
        any_handled = any_handled or handled
    if not any_handled:
        print("ℹ️ No domain packs were handled this boot (nothing found).")

# -----------------------------------------------------------------------------
# Boot entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # 1) Ensure skills are persisted
    load_boot_goals()

    # 2) Ensure domain packs are in UCS, saved to disk, and injected into KG
    preload_all_domain_packs()

    # (Optional) Fallback: older direct call (kept for compatibility)
    # This won’t persist to disk, so it’s safe but less durable:
    load_domain_packs_into_kg()