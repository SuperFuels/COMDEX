import json
import os
import threading

# ──────────────────────────────────────────────
# 🧠 Global Boot Guard
# Prevents Knowledge Graph reinitialization across reloads
# ──────────────────────────────────────────────
_boot_done = False
_boot_lock = threading.Lock()

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
from backend.modules.dimensions.containers.tesseract_hub import ensure_tesseract_hub

# ──────────────────────────────────────────────
# 🧠 Knowledge Graph Writer (Singleton Access)
# ──────────────────────────────────────────────
try:
    from backend.modules.knowledge_graph import get_writer
    _kg_writer_global = None

    def get_or_create_kg_writer():
        """
        Retrieve a shared KnowledgeGraphWriter instance.
        Creates it lazily on first call, then reuses the same one.
        """
        global _kg_writer_global
        if _kg_writer_global is None:
            _kg_writer_global = get_writer()
        return _kg_writer_global

    # Singleton alias for downstream imports
    kg_writer = get_or_create_kg_writer()
    print("[boot_loader] ✅ KnowledgeGraphWriter linked to global cache.")
except Exception as e:
    print(f"[boot_loader] ⚠️ Failed to import or initialize KnowledgeGraphWriter: {e}")
    kg_writer = None


# ──────────────────────────────────────────────
# 🧩 HQ / Tesseract Hub (idempotent creator)
# ──────────────────────────────────────────────
try:
    from backend.modules.dimensions.containers.tesseract_hub import ensure_tesseract_hub
except Exception:
    ensure_tesseract_hub = None  # safe no-op if module not present

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# --- Seeded UCS load (math_core, physics_core, problem_graphs) ----------------
SEEDS = [
    "backend/modules/dimensions/containers/math_core.dc.json",
    "backend/modules/dimensions/containers/physics_core.dc.json",
    "backend/modules/dimensions/containers/problem_graphs.dc.json",
]

def load_boot_goals() -> Optional[Dict[str, Any]]:
    """Load startup goals from MilestoneTracker or KG."""
    try:
        return MilestoneTracker.get_boot_goals()
    except Exception as e:
        print(f"[boot_loader] Failed to load boot goals: {e}")
        return None

def preload_all_domain_packs() -> None:
    """Preload all core .dc.json seeds into the UCS runtime."""
    for seed_path in SEEDS:
        try:
            if not Path(seed_path).exists():
                print(f"[boot_loader] Seed file missing: {seed_path}")
                continue
            with open(seed_path, "r", encoding="utf-8") as f:
                container_data = json.load(f)
            ucs_runtime.load_container(container_data)
            print(f"[boot_loader] Loaded seed: {seed_path}")
        except Exception as e:
            print(f"[boot_loader] Failed to load seed {seed_path}: {e}")

def boot():
    """Full boot sequence: load seeds, init KG, register DNA state."""
    global _boot_done
    with _boot_lock:
        if _boot_done:
            print("[boot_loader] ⏩ Boot sequence already completed — skipping re-run.")
            return

        print("[boot_loader] 🚀 Starting boot sequence...")

        # Ensure Tesseract HQ exists before anything links to it
        if ensure_tesseract_hub:
            try:
                ensure_tesseract_hub(hub_id="tesseract_hq", name="Tesseract HQ", size=8)
                print("[boot_loader] Tesseract HQ ensured (tesseract_hq).")
            except Exception as e:
                print(f"[boot_loader] ⚠️ Failed to ensure Tesseract HQ: {e}")

        # Load core seeds into UCS
        preload_all_domain_packs()

        # Load boot goals into KG (if any)
        boot_goals = load_boot_goals()
        if boot_goals and kg_writer:
            kg_writer.write_knowledge("boot_goals", boot_goals)

        _boot_done = True
        print("[boot_loader] ✅ Boot sequence complete (cached for future requests).")
    
def load_seed_containers():
    """
    Minimal UCS seed boot: load .dc.json files directly into ucs_runtime,
    and register any 'atoms' they contain.
    Safe to call multiple times (register_container is idempotent).
    """
    for p in SEEDS:
        if not os.path.exists(p):
            print(f"⚠️  seed missing: {p}")
            continue
        try:
            with open(p, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️  failed to read seed {p}: {e}")
            continue

        name = data.get("name") or data.get("id") or os.path.basename(p).split(".")[0]
        # persist raw container
        ucs_runtime.containers[name] = data
        ucs_runtime.active_container_name = name

        # register atoms (list or dict)
        atoms = data.get("atoms", [])
        if isinstance(atoms, list):
            for atom in atoms:
                try:
                    ucs_runtime.register_atom(name, atom)
                except Exception as e:
                    print(f"⚠️  atom skipped in {name}: {e}")
        elif isinstance(atoms, dict):
            for _, atom in atoms.items():
                try:
                    ucs_runtime.register_atom(name, atom)
                except Exception as e:
                    print(f"⚠️  atom skipped in {name}: {e}")

    # optional: see what UCS thinks now
    try:
        print("✅ Seed boot complete:", ucs_runtime.debug_state())
    except Exception:
        # if debug_state() doesn’t exist, this won’t crash boot
        pass

# -----------------------------------------------------------------------------
# Paths / Anchors
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
BOOTLOADER_FILE = os.path.join(BASE_DIR, "matrix_bootloader.json")
MEMORY_FILE = os.path.join(BASE_DIR, "aion_memory.json")

# This file lives at backend/modules/hexcore/boot_loader.py
# parents[0]=hexcore, [1]=modules, [2]=backend  → anchor here.
BACKEND_DIR = Path(__file__).resolve().parents[2]

# Domain seed & save locations (first that exists wins)
DOMAIN_SEED_DIRS = [
    BACKEND_DIR / "modules" / "dimensions" / "containers",                          # e.g. backend/modules/dimensions/containers/*.dc.json
    BACKEND_DIR / "modules" / "dimensions" / "ucs" / "containers",                  # alt location
    BACKEND_DIR / "modules" / "dimensions" / "universal_container_system" / "seeds" # alt location
]

# Where we persist domain packs we load
DOMAIN_SAVE_DIR = BACKEND_DIR / "modules" / "dimensions" / "containers_saved"
DOMAIN_SAVE_DIR.mkdir(parents=True, exist_ok=True)

# Where we export KG packs built from glyph_grid (for persistence/reload)
KG_EXPORT_DIR = DOMAIN_SAVE_DIR / "kg_exports"
KG_EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Utils: load/save JSON
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# Bootloader core: skills & memory sanitize
# -----------------------------------------------------------------------------
def load_boot_goals():
    # --- sanitize memory on disk first ---
    from backend.modules.hexcore.memory_engine import sanitize_memory_file_at
    sanitize_memory_file_at(MEMORY_FILE)

    # --- load + sanity checks ---
    boot_skills = load_json(BOOTLOADER_FILE)
    if not isinstance(boot_skills, list):
        print("⚠️ boot_loader: matrix_bootloader.json is not a list; coercing to empty list.")
        boot_skills = []

    memory_data = load_json(MEMORY_FILE)
    if not isinstance(memory_data, list):
        print("⚠️ boot_loader: aion_memory.json is not a list; coercing to empty list.")
        memory_data = []

    # guardrails (keep only dict rows with string titles)
    pre_len = len(memory_data)
    memory_data = [r for r in memory_data if isinstance(r, dict) and isinstance(r.get("title"), str)]
    if pre_len != len(memory_data):
        print(f"🧽 boot_loader: pruned {pre_len - len(memory_data)} malformed memory rows.")

    memory_titles = {entry["title"] for entry in memory_data}

    tracker = MilestoneTracker()
    updated_memory = list(memory_data)  # copy
    new_entries = []
    promoted_count = 0

    # Add new skills from bootloader file if missing
    for skill in boot_skills:
        title = skill.get("title")
        tags = skill.get("tags", [])
        if not isinstance(title, str):
            continue
        if title not in memory_titles:
            milestone_ready = tracker.is_milestone_triggered(tags)
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
                "learned_on": None,
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

# -----------------------------------------------------------------------------
# Seed resolution & persistence helpers — ensure domain packs survive restarts
# -----------------------------------------------------------------------------
def _resolve_dc_seed_path(container_id: str) -> Optional[Path]:
    """Find a seed .dc.json by ID, with debug so we see what’s happening."""
    filename = f"{container_id}.dc.json"
    tried = []
    for d in DOMAIN_SEED_DIRS:
        p = d / filename
        tried.append(str(p))
        if p.exists():
            return p
    print(f"ℹ️ seed not found for {container_id}. Tried:\n  - " + "\n  - ".join(tried))
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

# ─────────────────────────────────────────────────────────────────────────────
# Generic DC → KG ingest (fallback path used when no domain-specific handler)
# ─────────────────────────────────────────────────────────────────────────────
def _ingest_dc_into_kg(container: Dict[str, Any]) -> int:
    """
    Minimal generic ingest: add nodes, then edges.
    Returns number of injected glyphs (nodes+edges).
    """
    injected = 0
    try:
        for n in container.get("nodes", []) or []:
            nid   = n.get("id")
            label = n.get("label", nid or "node")
            meta  = {
                "source": container.get("id") or container.get("name"),
                "domain": container.get("metadata", {}).get("domain"),
                "category": n.get("cat"),
            }
            if nid:
                kg_writer.add_node(nid, label=label, meta=meta)
                injected += 1
        for e in container.get("links", []) or []:
            src = e.get("src")
            dst = e.get("dst")
            rel = e.get("relation", "relates_to")
            if src and dst:
                kg_writer.add_edge(src, dst, rel)
                injected += 1
    except Exception as e:
        print(f"⚠️ Generic DC→KG ingest failed: {e}")
    return injected


# ─────────────────────────────────────────────────────────────────────────────
# Apply cross_links after all other packs (idempotent)
# ─────────────────────────────────────────────────────────────────────────────
def _apply_cross_links_last() -> None:
    """
    Always apply 'cross_links' edges after all other packs are loaded.
    Safe no-op if cross_links is missing.
    """
    try:
        container = ucs_runtime.get_container("cross_links")
        if not (container and (container.get("links") or container.get("nodes"))):
            # try to load from disk/seed if not already present
            container = load_container_from_disk("cross_links")

        if not (container and container.get("links")):
            return

        # Attach so emitted glyphs land in the same KG/container space
        try:
            kg_writer.attach_container(container)
        except Exception:
            pass

        injected = 0
        for link in container.get("links", []) or []:
            src = link.get("src")
            dst = link.get("dst")
            rel = link.get("relation", "relates_to")
            if src and dst:
                try:
                    kg_writer.add_edge(src, dst, rel)
                    injected += 1
                except Exception as e:
                    print(f"⚠️ cross_links inject failed for {src}->{dst}: {e}")

        if injected:
            print(f"🧠 KG: cross_links applied ({injected} bridging edges).")
            # Export updated KG snapshot
            try:
                out = kg_writer.export_pack(container, str(KG_EXPORT_DIR / "cross_links.kg.json"))
                print(f"💾 KG export saved to {out}")
            except Exception as e:
                print(f"⚠️ KG export failed for cross_links: {e}")
    except Exception as e:
        print(f"⚠️ cross_links apply skipped: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Updated: preload + persist + inject + export (with cross_links special-case)
# ─────────────────────────────────────────────────────────────────────────────
def preload_and_persist_domain_pack(container_id: str) -> bool:
    """
    Ensure a domain pack is:
      1) available in UCS (load from disk/seed if missing)
      2) persisted to disk under containers_saved/
      3) written into KG so nodes/edges influence reasoning
      4) exported to KG_EXPORT_DIR as a replayable KG pack (.kg.json)
    Returns True if a pack was handled.
    """
    # 1) Ensure it's in UCS
    container = ucs_runtime.get_container(container_id)
    if not container or not container.get("nodes"):
        container = load_container_from_disk(container_id)

    if not container or not (container.get("nodes") or container.get("links")):
        print(f"ℹ️ Domain '{container_id}' not found on disk or seed; skipping.")
        return False

    # 2) Persist to disk (snap current UCS state)
    save_domain_pack_to_disk(container)

    # 3) Push into KG
    handled = False
    try:
        # Attach so glyphs land in this container’s space when possible
        try:
            kg_writer.attach_container(container)
        except Exception:
            pass

        # Special-case: cross_links is edges-only glue
        if container_id == "cross_links":
            injected = 0
            for link in container.get("links", []) or []:
                src = link.get("src")
                dst = link.get("dst")
                rel = link.get("relation", "relates_to")
                if src and dst:
                    try:
                        kg_writer.add_edge(src, dst, rel)
                        injected += 1
                    except Exception as e:
                        print(f"⚠️ cross_links inject failed for {src}->{dst}: {e}")
            handled = injected > 0
            print(f"🧠 KG: cross_links injected {injected} bridging edges.")
        else:
            # Preferred: domain-specific handler
            handled = kg_writer.load_domain_pack(container_id, container)
            if handled:
                print(f"🧠 KG: {container_id} domain loaded into Knowledge Graph.")
            else:
                # Fallback: generic ingest
                injected = _ingest_dc_into_kg(container)
                print(f"🧠 KG: {container_id} nodes/edges injected (generic, {injected}).")
                handled = injected > 0
    except Exception as e:
        print(f"⚠️ KG injection failed for {container_id}: {e}")

    # 4) Export KG pack built from glyph_grid (durable replay)
    try:
        out = kg_writer.export_pack(container, str(KG_EXPORT_DIR / f"{container_id}.kg.json"))
        print(f"💾 KG export saved to {out}")
    except Exception as e:
        print(f"⚠️ KG export failed for {container_id}: {e}")

    return handled


def preload_all_domain_packs():
    """
    One-stop boot: make sure all packs we care about are loaded and persisted.
    Then ALWAYS apply cross_links last to bridge domains.
    """
    targets = [
        "math_core",
        "physics_core",
        "control_systems",
        "engineering_materials",
        "biology_core",
        "economics_core",
        "cross_links",
        # "data_primary",          # D4.11 (enable when you have a seed)
        # "data_secondary",        # D4.12
        # "data_tertiary",         # D4.13
    ]
    any_handled = False
    for cid in targets:
        handled = preload_and_persist_domain_pack(cid)
        any_handled = any_handled or handled

    # Always bridge last
    _apply_cross_links_last()

    if not any_handled:
        print("ℹ️ No domain packs were handled this boot (nothing found).")


# -----------------------------------------------------------------------------
# Legacy compatibility: previous direct KG loader (kept)
# -----------------------------------------------------------------------------
def load_domain_packs_into_kg():
    """
    Pull domain containers from UCS and write them into the Knowledge Graph.
    Handles all targets below if present on disk/UCS.
    (Kept for compatibility with older runners; preload_all_domain_packs is preferred.)
    """
    targets = [
        "math_core",
        "physics_core",
        "control_systems",
        "engineering_materials",
        "biology_core",        # <- use the IDs that match your files on disk
        "economics_core",
        "cross_links",
    ]

    for domain in targets:
        try:
            container = ucs_runtime.get_container(domain)
            if not (container and (container.get("nodes") or container.get("links"))):
                print(f"ℹ️ KG: {domain} not present in UCS yet; skipping KG load.")
                continue

            # Make KG writer drop glyphs into the same container
            try:
                kg_writer.attach_container(container)
            except Exception:
                pass

            loaded = False

            # If not handled by writer and it's cross_links, inject edges here
            if domain == "cross_links":
                injected = 0
                for link in container.get("links", []) or []:
                    src = link.get("src")
                    dst = link.get("dst")
                    rel = link.get("relation", "relates_to")
                    if src and dst:
                        kg_writer.add_edge(src, dst, rel)
                        injected += 1
                loaded = injected > 0
                if loaded:
                    print(f"🧠 KG: cross_links injected {injected} bridging edges.")
            else:
                loaded = kg_writer.load_domain_pack(domain, container)

            if loaded:
                print(f"🧠 KG: {domain} domain loaded into Knowledge Graph.")
                # Export pack via boot path as well (redundant but explicit)
                out_path = DOMAIN_SAVE_DIR / "kg_exports" / f"{domain}.kg.json"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    kg_writer.export_pack(container, out_path)
                    print(f"💾 KG export saved to {out_path}")
                except Exception as e:
                    print(f"⚠️ KG export failed for {domain}: {e}")
            else:
                # Generic ingest fallback
                injected = _ingest_dc_into_kg(container)
                print(f"🧠 KG: {domain} nodes/edges injected (generic, {injected}).")
        except Exception as e:
            print(f"⚠️ KG domain load skipped for {domain}: {e}")

    # Always bridge last here too
    _apply_cross_links_last()

# -----------------------------------------------------------------------------
# Boot entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # 1) Ensure skills are persisted
    load_boot_goals()

    # 1.5) NEW: load seed containers (math_core, physics_core, problem_graphs) into UCS
    load_seed_containers()

    # 1.25) Ensure the permanent Tesseract HQ exists & is linked
    ensure_tesseract_hub(hub_id="tesseract_hq", name="Tesseract HQ", size=8)

    # 2) Ensure domain packs are in UCS, saved to disk, and injected into KG
    preload_all_domain_packs()

    # (Optional) legacy path still fine:
    load_domain_packs_into_kg()