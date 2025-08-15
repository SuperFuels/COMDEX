# backend/routes/ucs_api.py
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import os, json, inspect

from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime
from backend.modules.dna_chain.dna_address_lookup import register_container_address
from backend.modules.sqi.sqi_tessaris_bridge import (
    choose_route as sqi_choose_route,
    execute_route as sqi_execute_route,
)

router = APIRouter(prefix="/ucs", tags=["UCS"])

# --- Shims so we don't depend on UCSRuntime upgrades being applied yet --------
if not hasattr(ucs_runtime, "address_index"):
    ucs_runtime.address_index = {}

if not hasattr(ucs_runtime, "resolve_atom"):
    def _resolve_atom_shim(key: str) -> Optional[str]:
        if key in getattr(ucs_runtime, "atom_index", {}) or {}:
            return key
        return ucs_runtime.address_index.get(key)
    setattr(ucs_runtime, "resolve_atom", _resolve_atom_shim)

def _read_dc(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _infer_container_id(path: str, data: Dict[str, Any]) -> str:
    return data.get("id") or os.path.splitext(os.path.basename(path))[0]

def _maybe_register_atom(container_id: str, data: Dict[str, Any]) -> bool:
    """
    Register into ucs_runtime.atom_index using whichever register_atom
    signature is available. Also indexes meta.address if present.
    """
    if not hasattr(ucs_runtime, "register_atom"):
        return False

    # Prefer passing the full container dict so meta.address is visible
    meta = data.get("meta") or {}
    addr = meta.get("address")

    # Try new-style signature: (atom_id, atom_obj, container_name=None)
    try:
        sig = inspect.signature(ucs_runtime.register_atom)
        if "atom_obj" in sig.parameters:
            ucs_runtime.register_atom(atom_id=container_id, atom_obj=data, container_name=container_id)
        else:
            # Old-style: (container_name, atom)
            ucs_runtime.register_atom(container_id, data)
    except TypeError:
        # Fallback to old-style if the above still collides
        ucs_runtime.register_atom(container_id, data)
    except Exception:
        return False

    # Index the address if present
    if addr:
        ucs_runtime.address_index[addr] = container_id

    return True

@router.get("/debug")
def ucs_debug():
    debug_info: Dict[str, Any] = {}

    if hasattr(ucs_runtime, "debug_state"):
        try:
            debug_info = ucs_runtime.debug_state()
        except Exception as e:
            debug_info = {"error": f"debug_state() failed: {e}"}

    containers = list(getattr(ucs_runtime, "container_index", {}) or {})
    atoms      = list(getattr(ucs_runtime, "atom_index", {}) or {})
    addresses  = list(getattr(ucs_runtime, "address_index", {}) or {})
    atom_dir   = os.path.abspath("backend/data/ucs/atoms")

    debug_info.update({
        "containers": containers,
        "active_container": getattr(ucs_runtime, "active_container", None)
                            or getattr(ucs_runtime, "active_container_name", None)
                            or "Cross-Domain Links",
        "atom_index_count": len(atoms),
        "atom_ids": atoms,
        "addresses": addresses,
        "atom_dir_exists": os.path.exists(atom_dir),
        "atom_dir_path": atom_dir,
    })
    return debug_info

@router.post("/route")
def ucs_route(goal: Dict[str, Any]):
    try:
        plan = sqi_choose_route(goal)
        if not plan.get("atoms"):
            raise HTTPException(status_code=404, detail="No atoms matched the goal.")
        return plan
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute")
def ucs_execute(payload: Dict[str, Any]):
    plan = payload.get("plan")
    ctx  = payload.get("ctx", {}) or {}
    if not plan:
        raise HTTPException(status_code=400, detail="Missing 'plan' in body.")
    try:
        return sqi_execute_route(plan, ctx)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/resolve")
def ucs_resolve(payload: Dict[str, Any]):
    address = (payload.get("address") or "").strip()
    if not address:
        raise HTTPException(status_code=400, detail="Missing 'address' in body.")
    atom_id = ucs_runtime.resolve_atom(address)
    if not atom_id:
        raise HTTPException(status_code=404, detail="Not Found")
    return {"address": address, "atom_id": atom_id}

@router.post("/load")
def ucs_load(payload: Dict[str, Any]):
    """
    Body:
    {
      "path": "backend/modules/dimensions/containers/logic_core_atom.dc.json",
      "register_as_atom": true   # optional; auto-register if type == "atom"
    }
    """
    path: Optional[str] = payload.get("path")
    register_flag: bool = bool(payload.get("register_as_atom", False))

    if not path:
        raise HTTPException(status_code=400, detail="Missing 'path' in body.")

    try:
        # Read first so we can infer id/type/meta/address
        data = _read_dc(path)
        container_id = _infer_container_id(path, data)

        # Load into UCS memory/index
        if hasattr(ucs_runtime, "load_dc_container"):
            ucs_runtime.load_dc_container(path)   # typical loader
        else:
            # very old fallback
            if not hasattr(ucs_runtime, "containers"):
                ucs_runtime.containers = {}
            ucs_runtime.containers[container_id] = data
            setattr(ucs_runtime, "active_container", container_id)

        # Decide whether to register as atom
        should_register = register_flag or (data.get("type") == "atom")
        registered = False
        if should_register:
            # 1) put the whole container into the atom index (tuple style, 2 positional args ONLY)
            atom_spec = {
                "id": container_id,
                "type": data.get("type", "atom"),
                "meta": data.get("meta", {}) or {},
                "seed_glyphs": data.get("seed_glyphs", []),
                "ref": data,
            }
            ucs_runtime.register_atom(container_id, atom_spec)   # <-- no keyword args
            registered = True

            # 2) also push to the universal registry (so resolve by address works across reloads)
            try:
                meta = atom_spec.get("meta") or {}
                address = meta.get("address")
                # only write if we actually have an address string
                if isinstance(address, str) and address.strip():
                    register_container_address(
                        container_id=container_id,
                        address=address,
                        meta=meta,
                        kind=atom_spec.get("type", "atom"),
                    )
            except Exception:
                # soft-fail: address registry is optional
                pass

        return {
            "status": "ok",
            "container_id": container_id,
            "registered_as_atom": registered,
            "detected_type": data.get("type", "container"),
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Container file not found: {path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))