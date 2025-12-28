# backend/modules/lean/lean_batch.py
# -*- coding: utf-8 -*-

import argparse
import glob
import json
import os
from typing import List, Optional

from backend.modules.lean.lean_exporter import build_container_from_lean
from backend.modules.lean.lean_injector import (
    load_container,
    save_container,
    inject_theorems_into_container,
)


def _iter_lean(glob_or_dir: str) -> List[str]:
    if os.path.isdir(glob_or_dir):
        return sorted(
            [
                os.path.join(glob_or_dir, f)
                for f in os.listdir(glob_or_dir)
                if f.endswith(".lean")
            ]
        )
    return sorted(glob.glob(glob_or_dir))


def cmd_export(args: argparse.Namespace) -> int:
    os.makedirs(args.out_dir, exist_ok=True)
    count = 0

    for path in _iter_lean(args.source):
        try:
            container = build_container_from_lean(path, args.container_type)
            out_name = (
                os.path.splitext(os.path.basename(path))[0]
                + f".{args.container_type}.json"
            )
            out_path = os.path.join(args.out_dir, out_name)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(
                    container,
                    f,
                    indent=2 if args.pretty else None,
                    ensure_ascii=False,
                )
            print(f"[✅] {path} -> {out_path}")
            count += 1
        except Exception as e:
            print(f"[❌] export failed for {path}: {e}")

    print(f"\nDone. Exported {count} containers to {args.out_dir}")
    return 0


def _first_logic_field(container: dict) -> Optional[str]:
    for f in (
        "symbolic_logic",
        "expanded_logic",
        "hoberman_logic",
        "exotic_logic",
        "symmetric_logic",
        "axioms",
    ):
        if f in container and isinstance(container.get(f), list):
            return f
    return None


def cmd_inject(args: argparse.Namespace) -> int:
    before = load_container(args.container)
    current = before

    # ✅ apply flags during injection (so injector can do the right thing early)
    for path in _iter_lean(args.source):
        try:
            current = inject_theorems_into_container(
                current,
                path,
                overwrite=args.overwrite,
                normalize=args.normalize,
            )
        except TypeError:
            # Back-compat: older injector signature
            current = inject_theorems_into_container(current, path)
        except Exception as e:
            print(f"[❌] inject failed for {path}: {e}")

    # optional dedupe/overwrite post-pass (safety net)
    logic_field = _first_logic_field(current)
    if logic_field and (args.overwrite or args.dedupe):
        items = current.get(logic_field, [])

        if args.overwrite:
            by_name = {}
            for it in items:
                nm = it.get("name")
                if not nm:
                    continue
                by_name[nm] = it
            # keep unnamed entries too (rare but safe)
            unnamed = [it for it in items if not it.get("name")]
            items = list(by_name.values()) + unnamed

        if args.dedupe:
            seen, uniq = set(), []
            for it in items:
                sig = (
                    it.get("name"),
                    it.get("symbol"),
                    it.get("logic_raw") or it.get("logic"),
                )
                if sig in seen:
                    continue
                seen.add(sig)
                uniq.append(it)
            items = uniq

        current[logic_field] = items

    save_container(current, args.container)

    # pretty-print pass (optional)
    if args.pretty:
        with open(args.container, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)

    print(f"[✅] Batch injected into {args.container}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lean_batch", description="Batch Lean export/inject")
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("export", help="Export all .lean in a dir/glob to containers")
    pe.add_argument("source", help="Directory or glob for .lean files")
    pe.add_argument(
        "--container-type",
        "-t",
        choices=["dc", "hoberman", "sec", "exotic", "symmetry", "atom"],
        default="dc",
    )
    pe.add_argument("--out-dir", "-o", required=True, help="Output directory")
    pe.add_argument("--pretty", action="store_true")
    pe.set_defaults(func=cmd_export)

    pi = sub.add_parser("inject", help="Inject many .lean files into one container.json")
    pi.add_argument("source", help="Directory or glob for .lean files")
    pi.add_argument("--container", required=True, help="Target container JSON")
    pi.add_argument("--overwrite", action="store_true", help="Overwrite by name during inject")
    pi.add_argument("--dedupe", action="store_true", help="Dedupe by (name,symbol,logic)")
    pi.add_argument(
        "--normalize",
        action="store_true",
        help="Ask injector to normalize CodexLang (if supported)",
    )
    pi.add_argument("--pretty", action="store_true")
    pi.set_defaults(func=cmd_inject)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    # ✅ parse once
    p = build_parser()
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())