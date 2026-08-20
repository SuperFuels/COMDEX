#!/usr/bin/env python3
"""Give the detailed Boardroom robot an authored, independently shaded visor.

The June 2026 Blender export fused the robot into one mesh and one material and
duplicated vertices along many of the authored surface seams.  The rounded
facial visor therefore spans many disconnected index islands even though it is
one continuous visible panel.  This script identifies the complete recessed
front panel in model space and moves those original triangles into a dedicated
GLB primitive/material.  No replacement geometry is drawn over the face, so
the black surface follows the bespoke model exactly.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


GLB_HEADER = struct.Struct("<4sII")
CHUNK_HEADER = struct.Struct("<I4s")
UINT32 = struct.Struct("<I")


def _pad4(data: bytes, fill: bytes) -> bytes:
    return data + fill * ((-len(data)) % 4)


def _load_glb(path: Path) -> tuple[dict, bytearray]:
    payload = path.read_bytes()
    magic, version, total_length = GLB_HEADER.unpack_from(payload, 0)
    if magic != b"glTF" or version != 2 or total_length != len(payload):
        raise ValueError(f"{path} is not a valid GLB 2.0 file")

    offset = GLB_HEADER.size
    json_length, json_type = CHUNK_HEADER.unpack_from(payload, offset)
    offset += CHUNK_HEADER.size
    if json_type != b"JSON":
        raise ValueError("GLB JSON chunk is missing")
    document = json.loads(payload[offset : offset + json_length].decode("utf-8").rstrip(" \0"))
    offset += json_length

    binary_length, binary_type = CHUNK_HEADER.unpack_from(payload, offset)
    offset += CHUNK_HEADER.size
    if binary_type != b"BIN\0":
        raise ValueError("GLB BIN chunk is missing")
    return document, bytearray(payload[offset : offset + binary_length])


def _accessor_bytes(document: dict, binary: bytearray, accessor_index: int) -> memoryview:
    accessor = document["accessors"][accessor_index]
    view = document["bufferViews"][accessor["bufferView"]]
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    return memoryview(binary)[start : start + view["byteLength"]]


def _find_authored_visor(document: dict, binary: bytearray) -> tuple[set[int], list[int]]:
    primitive = document["meshes"][0]["primitives"][0]
    position_accessor = document["accessors"][primitive["attributes"]["POSITION"]]
    index_accessor = document["accessors"][primitive["indices"]]
    if position_accessor["componentType"] != 5126 or position_accessor["type"] != "VEC3":
        raise ValueError("Expected float32 VEC3 robot positions")
    if index_accessor["componentType"] != 5125 or index_accessor["type"] != "SCALAR":
        raise ValueError("Expected uint32 robot indices")

    position_data = _accessor_bytes(document, binary, primitive["attributes"]["POSITION"])
    index_data = _accessor_bytes(document, binary, primitive["indices"])
    positions = list(struct.iter_unpack("<fff", position_data[: position_accessor["count"] * 12]))
    indices = [value[0] for value in struct.iter_unpack("<I", index_data[: index_accessor["count"] * 4])]

    # The visible panel is an authored oval on the forward surface.  Its index
    # seams are fragmented, so connected-component selection only colours its
    # centre.  Select original triangles by their centroid inside the measured
    # panel envelope instead.  The depth limit includes the curved cheek edges
    # while excluding the white rear helmet shell.
    visor_vertices: set[int] = set()
    visor_triangle_offsets: set[int] = set()
    visor_triangles: list[int] = []
    centre_y = 1.455
    radius_x = 0.228
    radius_y = 0.196
    for offset in range(0, len(indices), 3):
        triangle = indices[offset : offset + 3]
        vertices = [positions[index] for index in triangle]
        centre_x = sum(value[0] for value in vertices) / 3.0
        centre_y_value = sum(value[1] for value in vertices) / 3.0
        centre_z = sum(value[2] for value in vertices) / 3.0
        oval = (centre_x / radius_x) ** 2 + ((centre_y_value - centre_y) / radius_y) ** 2
        if oval <= 1.08 and centre_z >= -0.12:
            visor_vertices.update(triangle)
            visor_triangle_offsets.add(offset)
            visor_triangles.extend(triangle)

    if not 12_000 <= len(visor_triangles) <= 13_500:
        raise ValueError(
            "Complete authored visor selection fell outside its validated triangle range: "
            f"{len(visor_triangles)} indices"
        )
    return visor_triangle_offsets, indices


def rebuild(source: Path, output: Path) -> dict[str, int]:
    document, binary = _load_glb(source)
    if len(document.get("meshes", [])) != 1 or len(document["meshes"][0].get("primitives", [])) != 1:
        raise ValueError("Expected the fused one-mesh/one-primitive Blender export")
    if any(material.get("name") == "aion_black_visor" for material in document.get("materials", [])):
        raise ValueError("This GLB already contains the authored AION visor material")

    visor_triangle_offsets, indices = _find_authored_visor(document, binary)
    body_indices: list[int] = []
    visor_indices: list[int] = []
    for offset in range(0, len(indices), 3):
        triangle = indices[offset : offset + 3]
        destination = visor_indices if offset in visor_triangle_offsets else body_indices
        destination.extend(triangle)
    if not visor_indices or len(body_indices) + len(visor_indices) != len(indices):
        raise ValueError("Visor triangle split failed validation")

    def append_indices(values: list[int]) -> int:
        while len(binary) % 4:
            binary.append(0)
        byte_offset = len(binary)
        binary.extend(struct.pack(f"<{len(values)}I", *values))
        view_index = len(document["bufferViews"])
        document["bufferViews"].append(
            {"buffer": 0, "byteOffset": byte_offset, "byteLength": len(values) * 4, "target": 34963}
        )
        accessor_index = len(document["accessors"])
        document["accessors"].append(
            {"bufferView": view_index, "componentType": 5125, "count": len(values), "type": "SCALAR"}
        )
        return accessor_index

    body_accessor = append_indices(body_indices)
    visor_accessor = append_indices(visor_indices)
    document["buffers"][0]["byteLength"] = len(binary)
    visor_material = len(document.setdefault("materials", []))
    document["materials"].append(
        {
            "name": "aion_black_visor",
            "doubleSided": True,
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.012, 0.012, 0.015, 1.0],
                "metallicFactor": 0.42,
                "roughnessFactor": 0.2,
            },
        }
    )

    source_primitive = document["meshes"][0]["primitives"][0]
    shared_attributes = dict(source_primitive["attributes"])
    body_primitive = {"attributes": shared_attributes, "indices": body_accessor, "material": source_primitive.get("material", 0)}
    visor_primitive = {"attributes": shared_attributes, "indices": visor_accessor, "material": visor_material}
    document["meshes"][0]["primitives"] = [body_primitive, visor_primitive]
    document.setdefault("asset", {})["extras"] = {
        **document.get("asset", {}).get("extras", {}),
        "aionVisorBuild": "complete authored facial panel split into dedicated primitive/material",
    }

    json_chunk = _pad4(json.dumps(document, separators=(",", ":")).encode("utf-8"), b" ")
    binary_chunk = _pad4(bytes(binary), b"\0")
    total_length = GLB_HEADER.size + CHUNK_HEADER.size + len(json_chunk) + CHUNK_HEADER.size + len(binary_chunk)
    payload = bytearray(GLB_HEADER.pack(b"glTF", 2, total_length))
    payload.extend(CHUNK_HEADER.pack(len(json_chunk), b"JSON"))
    payload.extend(json_chunk)
    payload.extend(CHUNK_HEADER.pack(len(binary_chunk), b"BIN\0"))
    payload.extend(binary_chunk)
    output.write_bytes(payload)
    return {
        "original_indices": len(indices),
        "body_indices": len(body_indices),
        "visor_indices": len(visor_indices),
        "visor_vertices": len(set(visor_indices)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = rebuild(args.source, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
