# backend/modules/lean/lean_inject_cli.py

import sys
import os
import json
import argparse
import difflib
import time
from typing import Any, Dict, List, Tuple, Optional

# Local imports (work with PYTHONPATH=.)
from backend.modules.lean.lean_injector import (
    inject_theorems_into_container,
    load_container,
    save_container,
)
from backend.modules.lean.lean_inject_utils import (
    guess_spec,
    auto_clean,
    dedupe_by_name,
    rebuild_previews,
)
from backend.modules.lean.lean_report import render_report
from backend.modules.lean.lean_exporter import build_container_from_lean
from backend.modules.lean.lean_audit import audit_event, build_inject_event
from backend.modules.lean.lean_ghx import dump_packets, bundle_packets
from backend.modules.lean.lean_proofviz import (
    ascii_tree_for_theorem,
    mermaid_for_dependencies,
    png_for_dependencies,
)

# --- Public map consumed by routes/lean_inject.py (imported as CONTAINER_MAP) ---
CONTAINER_MAP = {
    "DC":  "backend.modules.dimensions.universal_container_system.ucs_runtime",
    "SEC": "backend.modules.dimensions.containers.engineering_materials.dc",
    "HSC": "backend.modules.dimensions.hoberman_container",
}

# -----------------------------
# Shared GHX emission helper
# -----------------------------
def _maybe_emit_ghx(container: Dict[str, Any], args: argparse.Namespace) -> None:
    """
    Emit GHX packets/bundles from the *logic entries* in the container.
    Uses lean_ghx.py API: dump_packets(entries, out_dir, container_id=..., source_path=...)
                         bundle_packets(entries, out_file, container_id=..., source_path=...)
    """
    if not getattr(args, "ghx_out", None) and not getattr(args, "ghx_bundle", None):
        return

    logic_field, entries = _collect_logic_entries(container)
    container_id = container.get("id")

    # best-effort source path from first entry
    source_path = None
    if isinstance(entries, list) and entries:
        source_path = entries[0].get("source") or entries[0].get("source_file")

    if getattr(args, "ghx_out", None):
        try:
            dump_packets(
                entries,
                args.ghx_out,
                container_id=container_id,
                source_path=source_path,
            )
            print(f"[📦] Wrote GHX packets -> {args.ghx_out}")
        except Exception as e:
            print(f"[⚠️] GHX packet dump failed: {e}")

    if getattr(args, "ghx_bundle", None):
        try:
            bundle_packets(
                entries,
                args.ghx_bundle,
                container_id=container_id,
                source_path=source_path,
            )
            print(f"[📦] Wrote GHX bundle -> {args.ghx_bundle}")
        except Exception as e:
            print(f"[⚠️] GHX bundle failed: {e}")


# -----------------------------
# Small helpers / pretty output
# -----------------------------

def _print_summary(container: Dict[str, Any], logic_field_guess: Optional[str] = None) -> None:
    fields_in_priority = [
        logic_field_guess,
        "symbolic_logic",
        "expanded_logic",
        "hoberman_logic",
        "exotic_logic",
        "symmetric_logic",
        "axioms",
    ]
    logic_field = next((f for f in fields_in_priority if f and f in container), None)
    logic_items = container.get(logic_field, []) if logic_field else []
    print("\n- Summary -")
    print(f"type: {container.get('type')}")
    print(f"id:   {container.get('id')}")
    print(f"theorems/entries: {len(logic_items)}")
    previews = container.get("previews", [])
    if previews:
        print("\nPreviews:")
        for p in previews[:6]:
            print("  *", p)
        if len(previews) > 6:
            print(f"  ... (+{len(previews) - 6} more)")


def _diff_strings(a: str, b: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            a.splitlines(), b.splitlines(),
            fromfile="before.json", tofile="after.json", lineterm=""
        )
    )


# -----------------------------
# Reporting & Graph generation
# -----------------------------

def _collect_logic_entries(container: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    """Return (logic_field, entries) picking the best-known logic field."""
    for f in ("symbolic_logic", "expanded_logic", "hoberman_logic", "exotic_logic", "symmetric_logic", "axioms"):
        if f in container and isinstance(container[f], list):
            return f, container[f]
    return "symbolic_logic", container.get("symbolic_logic", [])


def _write_report(container: Dict[str, Any], kind: str, out: Optional[str]) -> None:
    """Use unified lean_report renderer to emit reports in md/json/html."""
    try:
        report = render_report(
            container,
            fmt=kind,
            kind="lean.inject",
            container_path=container.get("path") or "?",
            container_id=container.get("id"),
            lean_path=container.get("lean_path") or "?",
            validation_errors=container.get("validation_errors", []),
            origin="CLI",
        )
    except Exception as e:
        print(f"[⚠️] Failed to render report: {e}")
        return

    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"[📝] Wrote report -> {out}")
    else:
        print(report)


def _emit_dot(container: Dict[str, Any], dot_path: str) -> None:
    """Emit Graphviz DOT for theorem->dependency edges."""
    _, entries = _collect_logic_entries(container)
    names = {e.get("name"): True for e in entries if e.get("name")}
    lines = []
    lines.append("digraph G {")
    lines.append('  rankdir=LR;')
    lines.append('  node [shape=box, style="rounded,filled", fillcolor="#eef7ff"];')

    for e in entries:
        n = e.get("name")
        if not n:
            continue
        label = f'{n}\\n{e.get("symbol","")}'
        lines.append(f'  "{n}" [label="{label}"];')

    external_nodes = set()
    for e in entries:
        n = e.get("name")
        if not n:
            continue
        for d in e.get("depends_on", []):
            if d in names:
                lines.append(f'  "{n}" -> "{d}";')
            else:
                external_nodes.add(d)
                lines.append(f'  "{n}" -> "{d}" [style=dashed, color="#888"];')

    for d in sorted(external_nodes):
        safe = d.replace('"', '\\"')
        lines.append(f'  "{safe}" [shape=ellipse, style="dashed", color="#888"];')

    lines.append("}")
    with open(dot_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[📈] Wrote dependency graph DOT -> {dot_path}  (run: dot -Tpng {dot_path} -o deps.png)")


# -----------------------------
# Inject / Export commands
# -----------------------------

def _maybe_validate(container: Dict[str, Any], do_validate: bool) -> List[Dict[str, str]]:
    """
    Always compute and attach normalized validation errors to the container.
    If do_validate=True, also print the errors to stdout (CLI feedback).
    """
    from backend.modules.lean.lean_utils import validate_logic_trees, normalize_validation_errors

    raw_errors = validate_logic_trees(container)
    errors = normalize_validation_errors(raw_errors)

    container["validation_errors"] = errors
    container["validation_errors_version"] = "v1"

    if do_validate and errors:
        print("⚠️  Logic validation errors:")
        for e in errors:
            print(f"  * [{e['code']}] {e['message']}")

    return errors


def _auto_clean(container: Dict[str, Any]) -> None:
    """Remove empty arrays/dupes in glyphs/previews; keep structure tidy."""
    for key in ("glyphs", "previews"):
        if key in container and isinstance(container[key], list):
            seen = set()
            deduped = []
            for x in container[key]:
                if x not in seen:
                    seen.add(x)
                    deduped.append(x)
            container[key] = deduped
    for key in ("dependencies",):
        if key in container and not container[key]:
            del container[key]


def _integrated_hooks(container: Dict[str, Any]) -> None:
    """Placeholder: wire Codex/SQI hooks here."""
    print("[i️] Integrated mode: Codex/SQI hooks would run here.")


def cmd_inject(args: argparse.Namespace) -> int:
    try:
        before = load_container(args.container)

        after = inject_theorems_into_container(
            before,
            args.lean,
            normalize=args.normalize,
        )

        # Overwrite: replace rather than append (by name)
        if args.overwrite:
            field, items = _collect_logic_entries(after)
            name_to_latest = {it.get("name"): it for it in items}
            after[field] = list(name_to_latest.values())

        # Dedupe by (name, symbol, logic_raw)
        if args.dedupe:
            field, items = _collect_logic_entries(after)
            seen, unique = set(), []
            for it in items:
                sig = (it.get("name"), it.get("symbol"),
                       it.get("logic_raw") or it.get("logic"))
                if sig not in seen:
                    seen.add(sig)
                    unique.append(it)
            after[field] = unique

        # Preview mode
        if args.preview:
            if args.preview in ("raw", "normalized"):
                field, items = _collect_logic_entries(after)
                after["previews"] = []
                for it in items:
                    name = it.get("name", "unknown")
                    sym = it.get("symbol", "⟦ ? ⟧")
                    if args.preview == "raw":
                        logic_str = (
                            it.get("logic_raw")
                            or it.get("codexlang", {}).get("logic")
                            or it.get("logic")
                            or "???"
                        )
                    else:
                        logic_str = (
                            it.get("logic")
                            or it.get("logic_raw")
                            or it.get("codexlang", {}).get("logic")
                            or "???"
                        )
                    label = "Define" if "Definition" in sym else "Prove"
                    after["previews"].append(f"{sym} | {name} : {logic_str} -> {label} ⟧")

            elif args.preview == "mermaid":
                mmd = mermaid_for_dependencies(after)
                after["previews"] = [mmd]
                print("\n[🧭 Mermaid Preview]\n")
                print(mmd)

            elif args.preview == "png":
                out_path = args.container + ".preview.png"
                ok, msg = png_for_dependencies(after, out_path)
                after["previews"] = [out_path if ok else msg]
                print(("[✅] PNG preview saved -> " + out_path) if ok else ("[⚠️] " + msg))

        if args.auto_clean:
            _auto_clean(after)

        # ✅ single validation pass (attach always; print only if --validate)
        errors = _maybe_validate(after, args.validate)
        if args.fail_on_error and errors:
            print(f"[❌] Validation failed with {len(errors)} errors", file=sys.stderr)
            return 3

        if args.mode == "integrated":
            _integrated_hooks(after)
        else:
            print("[i️] Standalone mode: skipping Codex/SQI integration.")

        if args.summary:
            _print_summary(after)

        # Optional proof viz passthroughs
        if args.ascii:
            _, items = _collect_logic_entries(after)
            for e in items:
                print("\n" + "=" * 60)
                print(ascii_tree_for_theorem(e))

        if args.mermaid_out:
            mmd = mermaid_for_dependencies(after)
            with open(args.mermaid_out, "w", encoding="utf-8") as f:
                f.write(mmd)
            print(f"[🧭] wrote mermaid -> {args.mermaid_out}")

        if args.png_out:
            ok, msg = png_for_dependencies(after, args.png_out)
            print(("[✅] " + msg) if ok else ("[⚠️] " + msg))

        if args.dry_run or args.diff:
            before_s = json.dumps(before, indent=2, ensure_ascii=False)
            after_s = json.dumps(after, indent=2, ensure_ascii=False)
            if args.diff:
                print("\n- Diff -")
                print(_diff_strings(before_s, after_s))
            if args.dry_run:
                print("\n(dry-run) Not saving changes.")
                return 0

        # save in-place
        save_container(after, args.container)
        if args.pretty:
            with open(args.container, "w", encoding="utf-8") as f:
                json.dump(after, f, indent=2, ensure_ascii=False)

        # Reports / DOT after save so files match disk
        if args.report:
            _write_report(after, args.report, args.report_out)
        if args.dot:
            _emit_dot(after, args.dot)

        # 📝 Optional audit logging
        if args.log_audit:
            try:
                logic_field, items = _collect_logic_entries(after)
                audit_event(build_inject_event(
                    container_path=args.container,
                    container_id=after.get("id"),
                    lean_path=args.lean,
                    num_items=len(items),
                    previews=after.get("previews", []),
                    extra={"mode": args.mode, "normalize": args.normalize},
                ))
                print("[📝] Audit event logged")
            except Exception as e:
                print(f"[⚠️] Audit logging failed: {e}")

        # 📦 GHX packet output
        _maybe_emit_ghx(after, args)

        print(f"[✅] Injected Lean theorems into {args.container}")
        return 0

    except Exception as e:
        print(f"[❌] inject failed: {e}", file=sys.stderr)
        return 2


def cmd_export(args: argparse.Namespace) -> int:
    try:
        # ✅ exporter does NOT accept normalize=
        container = build_container_from_lean(args.lean, args.container_type)

        # ✅ single validation pass (attach always; print only if --validate)
        errors = _maybe_validate(container, args.validate)
        if args.fail_on_error and errors:
            print(f"[❌] Validation failed with {len(errors)} errors", file=sys.stderr)
            return 3

        if args.mode == "integrated":
            _integrated_hooks(container)
        else:
            print("[i️] Standalone mode: skipping Codex/SQI integration.")

        if args.summary:
            logic_hint = {
                "dc": "symbolic_logic",
                "hoberman": "hoberman_logic",
                "sec": "expanded_logic",
                "exotic": "exotic_logic",
                "symmetry": "symmetric_logic",
                "atom": "axioms",
            }.get(args.container_type, None)
            _print_summary(container, logic_hint)

        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(container, f, indent=2 if args.pretty else None, ensure_ascii=False)
            print(f"[✅] Wrote {args.container_type} container -> {args.out}")
        else:
            print(json.dumps(container, indent=2 if args.pretty else None, ensure_ascii=False))

        if args.report:
            _write_report(container, args.report, args.report_out)
        if args.dot:
            _emit_dot(container, args.dot)

        # 📦 GHX packet output
        _maybe_emit_ghx(container, args)

        return 0

    except Exception as e:
        print(f"[❌] export failed: {e}", file=sys.stderr)
        return 2


# -----------------------------
# Parser
# -----------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lean_inject", description="Lean->Glyph injection/export CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    # inject
    pi = sub.add_parser("inject", help="Inject Lean theorems into an existing container.json")
    pi.add_argument("container", help="Path to existing container JSON (modified in place)")
    pi.add_argument("lean", help="Path to .lean file")
    pi.add_argument("--dry-run", action="store_true", help="Do not save, just show what would change")
    pi.add_argument("--diff", action="store_true", help="Show unified diff before/after")
    pi.add_argument("--pretty", action="store_true", help="Pretty-print JSON on save")
    pi.add_argument("--summary", action="store_true", help="Print a short summary after inject")

    pi.add_argument("--overwrite", action="store_true", help="Replace existing entries with same name")
    pi.add_argument("--auto-clean", action="store_true", help="Trim duplicates/empties in glyphs/previews/deps")
    pi.add_argument("--dedupe", action="store_true", help="De-duplicate entries by (name,symbol,logic_raw)")
    pi.add_argument("--preview", choices=["raw", "normalized", "mermaid", "png"],
                    help="Generate previews: raw/normalized logic strings, or Mermaid/PNG diagrams")

    pi.add_argument("--validate", action="store_true", help="Print validation errors to stdout (always attached in JSON)")
    pi.add_argument("--fail-on-error", action="store_true", help="Exit with nonzero code if validation errors are found")

    pi.add_argument("--mode", choices=["standalone", "integrated"], default="integrated",
                    help="Execution mode (default: integrated)")
    pi.add_argument("--normalize", action="store_true",
                    help="Normalize via CodexLang (opt-in enrichment, default False)")

    pi.add_argument("--report", choices=["md", "json", "html"],
                    help="Emit a report (printed or saved with --report-out)")
    pi.add_argument("--report-out", help="Path to save the report (omit to print to stdout)")

    pi.add_argument("--dot", help="Write Graphviz DOT dependency graph to this path")

    pi.add_argument("--log-audit", action="store_true", help="Append an audit event to data/lean_audit.jsonl")
    pi.add_argument("--ghx-out", help="Directory to write one GHX packet per theorem")
    pi.add_argument("--ghx-bundle", help="Write a single GHX bundle JSON file")

    pi.add_argument("--ascii", action="store_true", help="Print ASCII tree per theorem")
    pi.add_argument("--mermaid-out", help="Write Mermaid .md")
    pi.add_argument("--png-out", help="Write dependency graph PNG (no graphviz needed)")

    pi.set_defaults(func=cmd_inject)

    # export
    pe = sub.add_parser("export", help="Export a .lean into a new container of a given type")
    pe.add_argument("lean", help="Path to .lean file")
    pe.add_argument("--container-type", "-t",
                    choices=["dc", "hoberman", "sec", "exotic", "symmetry", "atom"],
                    default="dc",
                    help="Target container layout (default: dc)")
    pe.add_argument("--out", "-o", help="Write to file instead of stdout")
    pe.add_argument("--pretty", action="store_true", help="Pretty-print output JSON")
    pe.add_argument("--summary", action="store_true", help="Print a short summary")

    pe.add_argument("--validate", action="store_true", help="Print validation errors to stdout (always attached in JSON)")
    pe.add_argument("--fail-on-error", action="store_true", help="Exit with nonzero code if validation errors are found")

    pe.add_argument("--mode", choices=["standalone", "integrated"], default="integrated",
                    help="Execution mode (default: integrated)")
    pe.add_argument("--normalize", action="store_true",
                    help="Normalize via CodexLang (opt-in enrichment, default False)")

    pe.add_argument("--report", choices=["md", "json", "html"],
                    help="Emit a report (printed or saved with --report-out)")
    pe.add_argument("--report-out", help="Path to save the report")
    pe.add_argument("--dot", help="Write Graphviz DOT dependency graph to this path")

    pe.add_argument("--ghx-out", help="Directory to write one GHX packet per theorem")
    pe.add_argument("--ghx-bundle", help="Write a single GHX bundle JSON file")

    pe.set_defaults(func=cmd_export)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())