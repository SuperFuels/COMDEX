import os
from pathlib import Path
from .glyph_compiler import compile_glyph, decompile_glyph

GLYPH_DIR = "dc_containers"

def get_microcube_path(container_id, coords):
    path = Path(GLYPH_DIR) / container_id / f"{coords[0]}_{coords[1]}_{coords[2]}.glyph"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

def write_glyph_to_microcube(container_id: str, coords: list, glyph: dict):
    bytecode = compile_glyph(glyph)
    path = get_microcube_path(container_id, coords)
    with open(path, "w") as f:
        f.write(bytecode)
    return {"status": "saved", "path": str(path), "bytecode": bytecode}

def read_glyph_from_microcube(container_id: str, coords: list):
    path = get_microcube_path(container_id, coords)
    if not path.exists():
        return {"status": "not_found", "coords": coords}
    with open(path, "r") as f:
        bytecode = f.read()
    glyph = decompile_glyph(bytecode)
    return {
        "status": "loaded",
        "coords": coords,
        "glyph": glyph,
        "bytecode": bytecode
    }

def scan_container_for_glyphs(container_id: str):
    container_path = Path(GLYPH_DIR) / container_id
    if not container_path.exists():
        return []
    glyphs = []
    for file in container_path.glob("*.glyph"):
        coords = list(map(int, file.stem.split("_")))
        with open(file, "r") as f:
            bytecode = f.read()
        glyphs.append({
            "coords": coords,
            "glyph": decompile_glyph(bytecode),
            "bytecode": bytecode
        })
    return glyphs