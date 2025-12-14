# File: backend/modules/hexcore/boot_loader.py

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Set

from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime

# ──────────────────────────────────────────────
# 🧠 Global Boot Guard
# Prevents Knowledge Graph reinitialization across reloads
# ──────────────────────────────────────────────
_boot_done = False
_boot_lock = threading.Lock()

# ──────────────────────────────────────────────
# 🧯 Boot seeding controls (ENV)
# Defaults are SAFE for uvicorn --reload (no KG re-seeding)
#
# Master switch (domain packs):
#   HEXCORE_PRELOAD_DOMAIN_PACKS=0/1
#
# Source selection:
#   HEXCORE_PRELOAD_FROM_SAVED=0/1   -> containers_saved/*.dc.json
#   HEXCORE_PRELOAD_FROM_SEED=0/1    -> seed dirs (containers/*.dc.json etc)
#
# Expensive side-effects:
#   HEXCORE_INJECT_TO_KG=0/1
#   HEXCORE_SAVE_TO_DISK=0/1
#   HEXCORE_EXPORT_KG_PACKS=0/1
#
# Filtering:
#   HEXCORE_PACK_ALLOW="math_core,physics_core"
#   HEXCORE_PACK_EXCLUDE="engineering_materials,biology_core"
#   (supports simple "*" wildcards)
#
# Optional targets override:
#   HEXCORE_DOMAIN_TARGETS="math_core,physics_core,cross_links"
# ──────────────────────────────────────────────

# -----------------------------------------------------------------------------
# Backwards-compat exports (KEEP: main.py imports these)
# -----------------------------------------------------------------------------

def load_boot_goals() -> Optional[Dict[str, Any]]:
    """
    Back-compat wrapper.
    Older code expects load_boot_goals() to exist.
    We keep it and do the cheap bootloader->memory sync,
    then return runtime boot goals (if any).
    """
    # sync matrix_bootloader.json -> aion_memory.json
    try:
        sync_bootloader_skills_to_memory()
    except Exception as e:
        print(f"[boot_loader] ⚠️ load_boot_goals: skill sync failed: {e}")

    # return runtime boot goals (used by some callers)
    return get_startup_boot_goals()

def _env_bool(name: str, default: str = "0") -> bool:
    v = os.getenv(name, default)
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

def _env_csv_set(name: str) -> Set[str]:
    return {s.strip() for s in str(os.getenv(name, "")).split(",") if s.strip()}

def _match_glob(pat: str, text: str) -> bool:
    """
    Minimal glob matcher: supports "*" wildcard only.
    """
    if "*" not in pat:
        return pat == text
    parts = pat.split("*")
    i = 0
    for part in parts:
        if not part:
            continue
        j = text.find(part, i)
        if j == -1:
            return False
        i = j + len(part)
    if not pat.endswith("*") and parts[-1]:
        return text.endswith(parts[-1])
    return True

# Core seeds (cheap, kept ON by default)
HEXCORE_PRELOAD_CORE_SEEDS = _env_bool("HEXCORE_PRELOAD_CORE_SEEDS", "1")

# Domain pack pipeline (this is what spams on reload) — OFF by default
HEXCORE_PRELOAD_DOMAIN_PACKS = _env_bool("HEXCORE_PRELOAD_DOMAIN_PACKS", "0")

HEXCORE_PRELOAD_FROM_SAVED = _env_bool("HEXCORE_PRELOAD_FROM_SAVED", "0")
HEXCORE_PRELOAD_FROM_SEED = _env_bool("HEXCORE_PRELOAD_FROM_SEED", "1")

HEXCORE_INJECT_TO_KG = _env_bool("HEXCORE_INJECT_TO_KG", "0")
HEXCORE_SAVE_TO_DISK = _env_bool("HEXCORE_SAVE_TO_DISK", "0")
HEXCORE_EXPORT_KG_PACKS = _env_bool("HEXCORE_EXPORT_KG_PACKS", "0")

HEXCORE_PACK_ALLOW = _env_csv_set("HEXCORE_PACK_ALLOW")
HEXCORE_PACK_EXCLUDE = _env_csv_set("HEXCORE_PACK_EXCLUDE")

HEXCORE_DOMAIN_TARGETS_ENV = os.getenv("HEXCORE_DOMAIN_TARGETS", "").strip()

def _pack_is_allowed(container_id: str = "", filename: str = "") -> bool:
    cid = (container_id or "").strip()
    fn = (filename or "").strip()
    base = fn.replace(".dc.json", "").replace(".kg.json", "").strip()

    # allowlist wins (if provided)
    if HEXCORE_PACK_ALLOW:
        ok = False
        for a in HEXCORE_PACK_ALLOW:
            if _match_glob(a, cid) or _match_glob(a, fn) or _match_glob(a, base):
                ok = True
                break
        if not ok:
            return False

    # exclude always applies
    for x in HEXCORE_PACK_EXCLUDE:
        if _match_glob(x, cid) or _match_glob(x, fn) or _match_glob(x, base):
            return False

    return True


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


# -----------------------------------------------------------------------------
# Paths / Anchors
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
BOOTLOADER_FILE = os.path.join(BASE_DIR, "matrix_bootloader.json")
MEMORY_FILE = os.path.join(BASE_DIR, "aion_memory.json")

# This file lives at backend/modules/hexcore/boot_loader.py
# parents[0]=hexcore, [1]=modules, [2]=backend  -> anchor here.
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
def sync_bootloader_skills_to_memory() -> None:
    """
    Reads matrix_bootloader.json and merges into aion_memory.json, with sanitation.
    (This is the *file-based bootloader* path.)
    """
    try:
        from backend.modules.hexcore.memory_engine import sanitize_memory_file_at
        sanitize_memory_file_at(MEMORY_FILE)
    except Exception as e:
        print(f"⚠️ boot_loader: memory sanitize skipped: {e}")

    boot_skills = load_json(BOOTLOADER_FILE)
    if not isinstance(boot_skills, list):
        print("⚠️ boot_loader: matrix_bootloader.json is not a list; coercing to empty list.")
        boot_skills = []

    memory_data = load_json(MEMORY_FILE)
    if not isinstance(memory_data, list):
        print("⚠️ boot_loader: aion_memory.json is not a list; coercing to empty list.")
        memory_data = []

    pre_len = len(memory_data)
    memory_data = [r for r in memory_data if isinstance(r, dict) and isinstance(r.get("title"), str)]
    if pre_len != len(memory_data):
        print(f"🧽 boot_loader: pruned {pre_len - len(memory_data)} malformed memory rows.")

    memory_titles = {entry["title"] for entry in memory_data}

    tracker = MilestoneTracker()
    updated_memory = list(memory_data)
    new_entries = []
    promoted_count = 0

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

    for entry in updated_memory:
        if entry.get("status") == "ready" and dependencies_met(entry, updated_memory):
            entry["status"] = "queued"
            promoted_count += 1

    if promoted_count > 0:
        print(f"⬆️ Promoted {promoted_count} skills from 'ready' to 'queued' based on dependencies.")

    save_json(MEMORY_FILE, updated_memory)

    if not new_entries and promoted_count == 0:
        print("i️ No new bootloader skills added or promoted. Memory is up to date.")


def get_startup_boot_goals() -> Optional[Dict[str, Any]]:
    """
    Pull *runtime* boot goals from MilestoneTracker (if implemented).
    This is separate from sync_bootloader_skills_to_memory().
    """
    try:
        return MilestoneTracker.get_boot_goals()
    except Exception as e:
        print(f"[boot_loader] Failed to load boot goals: {e}")
        return None


# -----------------------------------------------------------------------------
# Core seed loading (cheap)
# -----------------------------------------------------------------------------
def preload_core_seeds_into_ucs() -> None:
    """Load the small SEEDS list into UCS runtime."""
    if not HEXCORE_PRELOAD_CORE_SEEDS:
        return

    for seed_path in SEEDS:
        try:
            if not Path(seed_path).exists():
                print(f"[boot_loader] Seed file missing: {seed_path}")
                continue
            with open(seed_path, "r", encoding="utf-8") as f:
                container_data = json.load(f)
            # Some implementations accept dict directly; others accept path.
            try:
                ucs_runtime.load_container(container_data)
            except Exception:
                ucs_runtime.load_container(seed_path)
            print(f"[boot_loader] Loaded seed: {seed_path}")
        except Exception as e:
            print(f"[boot_loader] Failed to load seed {seed_path}: {e}")


def load_seed_containers() -> None:
    """
    Minimal UCS seed boot: load .dc.json files directly into ucs_runtime,
    and register any 'atoms' they contain.
    Safe to call multiple times.
    """
    if not HEXCORE_PRELOAD_CORE_SEEDS:
        return

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
        ucs_runtime.containers[name] = data
        ucs_runtime.active_container_name = name

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

    try:
        print("✅ Seed boot complete:", ucs_runtime.debug_state())
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Seed resolution & persistence helpers - ensure domain packs survive restarts
# -----------------------------------------------------------------------------
def _resolve_dc_seed_path(container_id: str) -> Optional[Path]:
    """Find a seed .dc.json by ID, with debug so we see what's happening."""
    filename = f"{container_id}.dc.json"
    tried = []
    for d in DOMAIN_SEED_DIRS:
        p = d / filename
        tried.append(str(p))
        if p.exists():
            return p
    print(f"i️ seed not found for {container_id}. Tried:\n  - " + "\n  - ".join(tried))
    return None

def _get_saved_dc_path(container_id: str) -> Path:
    """Where we persist domain packs we've loaded."""
    return DOMAIN_SAVE_DIR / f"{container_id}.dc.json"

def save_domain_pack_to_disk(container: Dict[str, Any]) -> Optional[Path]:
    """Persist a container dict to disk so it's available at next boot."""
    if not HEXCORE_SAVE_TO_DISK:
        return None
    if not container or not isinstance(container, dict):
        return None
    cid = container.get("id") or container.get("name")
    if not cid:
        return None
    if not _pack_is_allowed(container_id=str(cid), filename=f"{cid}.dc.json"):
        return None

    path = _get_saved_dc_path(str(cid))
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
    if not _pack_is_allowed(container_id=container_id, filename=f"{container_id}.dc.json"):
        return None

    saved = _get_saved_dc_path(container_id)
    seed = _resolve_dc_seed_path(container_id)
    picked: Optional[Path] = None

    # Prefer saved only if enabled
    if HEXCORE_PRELOAD_FROM_SAVED and saved.exists():
        picked = saved
    # Seed fallback only if enabled
    elif HEXCORE_PRELOAD_FROM_SEED and seed is not None:
        picked = seed

    if not picked:
        return None

    existing = ucs_runtime.get_container(container_id)
    if not existing or not existing.get("id"):
        try:
            name = ucs_runtime.load_container(str(picked))
            print(f"📦 Loaded '{name}' container from {picked}")
        except Exception as e:
            print(f"⚠️ Failed to load container {container_id} from {picked}: {e}")

    return ucs_runtime.get_container(container_id)


# ─────────────────────────────────────────────────────────────────────────────
# Generic DC -> KG ingest (fallback path used when no domain-specific handler)
# ─────────────────────────────────────────────────────────────────────────────
def _ingest_dc_into_kg(container: Dict[str, Any]) -> int:
    """
    Minimal generic ingest: add nodes, then edges.
    Returns number of injected glyphs (nodes+edges).
    """
    if not (HEXCORE_INJECT_TO_KG and kg_writer):
        return 0

    injected = 0
    try:
        for n in container.get("nodes", []) or []:
            nid = n.get("id")
            label = n.get("label", nid or "node")
            meta = {
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
        print(f"⚠️ Generic DC->KG ingest failed: {e}")

    return injected


# ─────────────────────────────────────────────────────────────────────────────
# Apply cross_links after all other packs (idempotent)
# ─────────────────────────────────────────────────────────────────────────────
def _apply_cross_links_last() -> None:
    """
    Always apply 'cross_links' edges after all other packs are loaded.
    Safe no-op if cross_links is missing.
    """
    if not (HEXCORE_INJECT_TO_KG and kg_writer):
        return
    if not _pack_is_allowed(container_id="cross_links", filename="cross_links.dc.json"):
        return

    try:
        container = ucs_runtime.get_container("cross_links")
        if not (container and (container.get("links") or container.get("nodes"))):
            container = load_container_from_disk("cross_links")

        if not (container and container.get("links")):
            return

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

            if HEXCORE_EXPORT_KG_PACKS:
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
      2) optionally persisted to disk under containers_saved/
      3) optionally written into KG so nodes/edges influence reasoning
      4) optionally exported to KG_EXPORT_DIR as a replayable KG pack (.kg.json)
    Returns True if a pack was handled.
    """
    if not HEXCORE_PRELOAD_DOMAIN_PACKS:
        return False
    if not _pack_is_allowed(container_id=container_id, filename=f"{container_id}.dc.json"):
        return False

    # 1) Ensure it's in UCS
    container = ucs_runtime.get_container(container_id)
    if not container or not (container.get("nodes") or container.get("links")):
        container = load_container_from_disk(container_id)

    if not container or not (container.get("nodes") or container.get("links")):
        print(f"i️ Domain '{container_id}' not found on disk/seed (or disabled); skipping.")
        return False

    # 2) Persist to disk (snap current UCS state)
    save_domain_pack_to_disk(container)

    handled = False

    # 3) Push into KG (gated)
    if HEXCORE_INJECT_TO_KG and kg_writer:
        try:
            try:
                kg_writer.attach_container(container)
            except Exception:
                pass

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
                if injected:
                    print(f"🧠 KG: cross_links injected {injected} bridging edges.")
            else:
                loaded = False
                try:
                    loaded = bool(kg_writer.load_domain_pack(container_id, container))
                except Exception:
                    loaded = False

                if loaded:
                    handled = True
                    print(f"🧠 KG: {container_id} domain loaded into Knowledge Graph.")
                else:
                    injected = _ingest_dc_into_kg(container)
                    handled = injected > 0
                    print(f"🧠 KG: {container_id} nodes/edges injected (generic, {injected}).")

        except Exception as e:
            print(f"⚠️ KG injection failed for {container_id}: {e}")

    # 4) Export KG pack (gated)
    if HEXCORE_EXPORT_KG_PACKS and kg_writer:
        try:
            out = kg_writer.export_pack(container, str(KG_EXPORT_DIR / f"{container_id}.kg.json"))
            print(f"💾 KG export saved to {out}")
        except Exception as e:
            print(f"⚠️ KG export failed for {container_id}: {e}")

    return handled


def _default_domain_targets() -> List[str]:
    return [
        "math_core",
        "physics_core",
        "control_systems",
        "engineering_materials",
        "biology_core",
        "economics_core",
        "cross_links",
        # "data_primary",
        # "data_secondary",
        # "data_tertiary",
    ]

def _get_domain_targets() -> List[str]:
    if HEXCORE_DOMAIN_TARGETS_ENV:
        return [s.strip() for s in HEXCORE_DOMAIN_TARGETS_ENV.split(",") if s.strip()]
    return _default_domain_targets()

def preload_all_domain_packs() -> None:
    """
    One-stop boot: load/persist/inject/export domain packs.
    This is the path that caused your reload spam, so it is OFF by default.
    """
    if not HEXCORE_PRELOAD_DOMAIN_PACKS:
        print("⏭️ HEXCORE_PRELOAD_DOMAIN_PACKS=0 (skipping domain pack preload).")
        return

    any_handled = False
    for cid in _get_domain_targets():
        if not _pack_is_allowed(container_id=cid, filename=f"{cid}.dc.json"):
            continue
        handled = preload_and_persist_domain_pack(cid)
        any_handled = any_handled or handled

    _apply_cross_links_last()

    if not any_handled:
        print("i️ No domain packs were handled this boot.")


# -----------------------------------------------------------------------------
# Legacy compatibility: previous direct KG loader (kept, but gated)
# -----------------------------------------------------------------------------
def load_domain_packs_into_kg() -> None:
    """
    Legacy path: pulls domain containers from UCS and writes them into KG.
    Gated by HEXCORE_PRELOAD_DOMAIN_PACKS + HEXCORE_INJECT_TO_KG.
    """
    if not (HEXCORE_PRELOAD_DOMAIN_PACKS and HEXCORE_INJECT_TO_KG and kg_writer):
        print("⏭️ Domain KG load disabled (HEXCORE_PRELOAD_DOMAIN_PACKS=0 or HEXCORE_INJECT_TO_KG=0).")
        return

    for domain in _get_domain_targets():
        if not _pack_is_allowed(container_id=domain, filename=f"{domain}.dc.json"):
            continue
        try:
            container = ucs_runtime.get_container(domain)
            if not (container and (container.get("nodes") or container.get("links"))):
                continue

            try:
                kg_writer.attach_container(container)
            except Exception:
                pass

            loaded = False

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
                try:
                    loaded = bool(kg_writer.load_domain_pack(domain, container))
                except Exception:
                    loaded = False

            if not loaded:
                injected = _ingest_dc_into_kg(container)
                loaded = injected > 0

            if loaded:
                print(f"🧠 KG: {domain} loaded into Knowledge Graph.")

                if HEXCORE_EXPORT_KG_PACKS:
                    out_path = DOMAIN_SAVE_DIR / "kg_exports" / f"{domain}.kg.json"
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        kg_writer.export_pack(container, out_path)
                        print(f"💾 KG export saved to {out_path}")
                    except Exception as e:
                        print(f"⚠️ KG export failed for {domain}: {e}")

        except Exception as e:
            print(f"⚠️ KG domain load skipped for {domain}: {e}")

    _apply_cross_links_last()


# -----------------------------------------------------------------------------
# Boot sequence (what startup hooks should call)
# -----------------------------------------------------------------------------
def boot() -> None:
    """
    Full boot sequence: ensure HQ, load seeds, optionally preload domain packs,
    and optionally write runtime boot goals into KG.
    """
    global _boot_done
    with _boot_lock:
        if _boot_done:
            print("[boot_loader] ⏩ Boot sequence already completed - skipping re-run.")
            return

        print("[boot_loader] 🚀 Starting boot sequence...")

        if ensure_tesseract_hub:
            try:
                ensure_tesseract_hub(hub_id="tesseract_hq", name="Tesseract HQ", size=8)
                print("[boot_loader] Tesseract HQ ensured (tesseract_hq).")
            except Exception as e:
                print(f"[boot_loader] ⚠️ Failed to ensure Tesseract HQ: {e}")

        # Core seeds (cheap)
        preload_core_seeds_into_ucs()

        # File bootloader -> memory sync (cheap)
        try:
            sync_bootloader_skills_to_memory()
        except Exception as e:
            print(f"[boot_loader] ⚠️ Bootloader skill sync failed: {e}")

        # Domain packs (expensive) — gated OFF by default
        try:
            preload_all_domain_packs()
        except Exception as e:
            print(f"[boot_loader] ⚠️ Domain pack preload failed: {e}")

        # Runtime boot goals -> KG (also gated by KG switch)
        if HEXCORE_INJECT_TO_KG and kg_writer:
            boot_goals = get_startup_boot_goals()
            if boot_goals:
                try:
                    kg_writer.write_knowledge("boot_goals", boot_goals)
                except Exception as e:
                    print(f"[boot_loader] ⚠️ Failed to write boot_goals into KG: {e}")

        _boot_done = True
        print("[boot_loader] ✅ Boot sequence complete (cached for future requests).")


# -----------------------------------------------------------------------------
# CLI / direct execution
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sync_bootloader_skills_to_memory()
    load_seed_containers()

    if ensure_tesseract_hub:
        ensure_tesseract_hub(hub_id="tesseract_hq", name="Tesseract HQ", size=8)

    preload_all_domain_packs()
    load_domain_packs_into_kg()