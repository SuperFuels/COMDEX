# backend/modules/runtime/container_path_utils.py

import os

def container_id_to_path(container_id: str) -> str:
    """
    Maps a container ID like 'dc_xyz123' to the corresponding local file path.
    """
    if container_id.startswith("dc_"):
        return f"./containers/{container_id}.dc.json"
    elif container_id.startswith("atom_"):
        return f"./containers/atoms/{container_id}.dc.json"
    elif container_id.startswith("hoberman_"):
        return f"./containers/hoberman/{container_id}.dc.json"
    elif container_id.startswith("sec_"):
        return f"./containers/sec/{container_id}.dc.json"
    elif container_id.startswith("symmetry_"):
        return f"./containers/symmetry/{container_id}.dc.json"
    elif container_id.startswith("exotic_"):
        return f"./containers/exotic/{container_id}.dc.json"
    elif container_id.startswith("ucs_"):
        return f"./containers/ucs/{container_id}.dc.json"
    elif container_id.startswith("qfc_"):
        return f"./containers/qfc/{container_id}.dc.json"
    else:
        raise ValueError(f"Unknown container prefix for ID: {container_id}")