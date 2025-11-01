import os
if os.getenv("PHOTON_IMPORT", "1") not in ("0", "false", "False"):
    try:
        from backend.modules.photonlang.runtime import photon_importer as _ph
        _ph.install()
    except Exception as e:
        print(f"[photon] import hook not installed: {e}")
