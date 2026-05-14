from modules.dna_chain.luxnet_encoder import encrypt_and_encode
import json
import os

BUNDLE_DIR = "./bundles"
os.makedirs(BUNDLE_DIR, exist_ok=True)

def package_container_bundle(container_id: str, avatar_state: dict, glyph_snapshot: dict, metadata: dict) -> str:
    bundle = {
        "container": container_id,
        "avatar": avatar_state,
        "glyphs": glyph_snapshot,
        "metadata": metadata
    }
    
    encoded = encrypt_and_encode(bundle)
    filename = os.path.join(BUNDLE_DIR, f"bundle_{container_id}.lux")

    try:
        with open(filename, "w") as f:
            f.write(encoded)
        print(f"[BundleTransporter] Bundle written to {filename}")
        return filename
    except Exception as e:
        print(f"[BundleTransporter] Failed to write bundle: {e}")
        return ""
