from __future__ import annotations
import argparse, importlib
from backend.modules.photonlang.runtime import photon_importer

def main(argv=None):
    ap = argparse.ArgumentParser(description="Run a module stored as .photon/.pthon")
    ap.add_argument("module", help="Dotted module name (e.g. demo)")
    ap.add_argument("--call", help="Optional function to call after import (e.g. main)")
    args = ap.parse_args(argv)

    photon_importer.install()
    mod = importlib.import_module(args.module)
    if args.call:
        fn = getattr(mod, args.call)
        fn()

if __name__ == "__main__":
    main()