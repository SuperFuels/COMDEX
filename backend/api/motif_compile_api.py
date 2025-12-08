# backend/api/motif_compile_api.py
# Minimal Photon-motif stub → GHX / .holo compiler API

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Tuple
import re

# 👇 FIXED: no leading /api here
router = APIRouter(prefix="/motif", tags=["motif"])

# ---------- Request / response models ----------

class MotifCompileOptions(BaseModel):
    holo: bool = False  # if true, also wrap in a HoloIR-like object


class MotifCompileRequest(BaseModel):
    source: str
    options: Optional[MotifCompileOptions] = None


class MotifCompileResponse(BaseModel):
    kind: str
    ghx: Dict[str, Any]
    holo: Optional[Dict[str, Any]] = None


# ---------- Simple motif stub parser ----------

# Header comment line:
# # holo:holo:crystal::user:devtools:motif=motif:0007/t=7/v=1
MOTIF_HEADER_RE = re.compile(
    r"#\s*holo:holo:crystal::user:devtools:motif=(?P<motif>[^/]+)/t=(?P<t>\d+)/v=(?P<v>\d+)",
)

# We tolerate any container here, but keep the info in metadata if present
CONTAINER_HEADER_RE = re.compile(
    r"#\s*container:(?P<container>.+)$",
)

NODE_RE = re.compile(r'node\s+"([^"]+)"')
LINK_RE = re.compile(r'link\s+"([^"]+)"\s*->\s*"([^"]+)"')


def compile_motif_stub(source: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Parse the Photon motif stub syntax into a GHX packet plus a simple Holo-ish wrapper.
    """
    motif_id: Optional[str] = None
    tick: Optional[int] = None
    revision: Optional[int] = None
    container_id: str = "crystal::user:devtools"

    nodes: set[str] = set()
    edges: List[Tuple[str, str]] = []

    for line in source.splitlines():
        raw = line.rstrip("\n")
        s = raw.strip()
        if not s:
            continue

        # Comments
        if s.startswith("#"):
            m = MOTIF_HEADER_RE.match(s)
            if m:
                motif_id = m.group("motif")
                try:
                    tick = int(m.group("t"))
                except ValueError:
                    tick = None
                try:
                    revision = int(m.group("v"))
                except ValueError:
                    revision = None
                continue

            m = CONTAINER_HEADER_RE.match(s)
            if m:
                container_id = m.group("container").strip()
                continue

            # other comment → ignore
            continue

        # Nodes
        m = NODE_RE.match(s)
        if m:
            nodes.add(m.group(1))
            continue

        # Edges
        m = LINK_RE.match(s)
        if m:
            edges.append((m.group(1), m.group(2)))
            continue

        # Everything else: ignore for now (motif name line, TODO comments, etc.)

    if not nodes:
        raise ValueError("No nodes found in motif stub.")
    if not motif_id:
        motif_id = "motif:unknown"

    # Build GHX packet
    ghx_nodes = [
        {
            "id": n,
            "data": {
                "label": n,
                "kind": "motif_node",
            },
        }
        for n in sorted(nodes)
    ]

    ghx_edges = [
        {
            "id": f"e{i}",
            "src": src,
            "dst": dst,
            "kind": "motif_edge",
        }
        for i, (src, dst) in enumerate(edges)
    ]

    ghx: Dict[str, Any] = {
        "ghx_version": "1.0",
        "origin": "motif:photon",
        "container_id": container_id,
        "nodes": ghx_nodes,
        "edges": ghx_edges,
        "metadata": {
            "motif": {
                "id": motif_id,
                "tick": tick,
                "revision": revision,
                "node_count": len(ghx_nodes),
                "edge_count": len(ghx_edges),
            }
        },
    }

    # Build a lightweight Holo wrapper. You can adapt this to your existing HoloIR schema.
    next_revision = (revision or 0) + 1
    holo_id = f"holo:crystal::user:devtools:motif={motif_id}/t={tick or 0}/v={next_revision}"

    holo: Dict[str, Any] = {
        "holo_id": holo_id,
        "container_id": container_id,
        "tick": tick or 0,
        "revision": next_revision,
        "ghx": ghx,
        "metadata": ghx["metadata"],
    }

    return ghx, holo


# ---------- API route ----------

@router.post("/compile", response_model=MotifCompileResponse)
def motif_compile(payload: MotifCompileRequest) -> MotifCompileResponse:
    try:
        ghx, holo = compile_motif_stub(payload.source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Motif compile failed: {e}")

    want_holo = (payload.options or MotifCompileOptions()).holo

    return MotifCompileResponse(
        kind="photon_motif",
        ghx=ghx,
        holo=holo if want_holo else None,
    )