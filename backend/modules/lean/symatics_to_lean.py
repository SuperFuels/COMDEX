from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional, Set

DeclKind = Literal["def", "axiom", "theorem", "lemma", "constant"]

PRELUDE_SPROP = {"SProp", "False", "True"}
PRELUDE_PHASE = {"Phase", "zero_phase", "pi_phase"}
PRELUDE_FUNS = {"sInterf"}
RESERVED = {
    "import", "namespace", "end", "section", "variable", "variables",
    "theorem", "lemma", "axiom", "def", "constant",
    "by", "simp", "simpa", "exact", "intro", "apply", "have", "show",
    "let", "in", "match", "with", "fun",
}

def _sanitize_ident(name: str) -> str:
    out = "".join(ch if (ch.isalnum() or ch in "_'") else "_" for ch in (name or ""))
    out = out.strip("_") or "symatics_decl"
    if out[0].isdigit():
        out = "_" + out
    return out

def _extract_phase_terms(expr: str) -> Set[str]:
    terms: Set[str] = set()
    for m in re.finditer(r"⋈\[(.*?)\]", expr):
        raw = (m.group(1) or "").strip()
        if raw:
            terms.add(raw)
    return terms

def _extract_identifiers(expr: str) -> Set[str]:
    return set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_']*\b", expr))

@dataclass
class SymaticsLeanSpec:
    name: str = "symatics_test"
    kind: DeclKind = "def"
    use_prelude: bool = True
    namespace: Optional[str] = "Symatics"
    params: str = ""
    extra_header: str = ""
    proof: Optional[str] = None  # optional RHS proof/term

def symatics_to_lean(expr: str, spec: SymaticsLeanSpec | None = None) -> str:
    spec = spec or SymaticsLeanSpec()
    name = _sanitize_ident(spec.name)
    kind = spec.kind

    header = ""
    if spec.use_prelude:
        header += "import Tessaris.Symatics.Prelude\nimport Tessaris.Symatics.Axioms\n"
    if spec.extra_header.strip():
        header += spec.extra_header.rstrip() + "\n"

    ns_open = f"\nnamespace {spec.namespace}\n" if spec.namespace else "\n"
    ns_close = f"\nend {spec.namespace}\n" if spec.namespace else "\n"

    expr_s = (expr or "").strip() or "False"

    phase_terms = _extract_phase_terms(expr_s)
    ids = _extract_identifiers(expr_s)

    ids -= RESERVED
    ids -= PRELUDE_SPROP
    ids -= PRELUDE_PHASE
    ids -= PRELUDE_FUNS
    ids.discard(name)

    phase_vars = {p for p in phase_terms if p and p not in PRELUDE_PHASE and p not in RESERVED}
    sprop_vars = ids

    var_lines = []
    if sprop_vars:
        var_lines.append("variable " + " ".join(f"({v} : SProp)" for v in sorted(sprop_vars)))
    if phase_vars:
        var_lines.append("variable " + " ".join(f"({v} : Phase)" for v in sorted(phase_vars)))
    vars_block = ("\n" + "\n".join(var_lines) + "\n") if var_lines else "\n"

    params = f" {spec.params.strip()}" if spec.params.strip() else ""

    if kind == "def":
        rhs = spec.proof.strip() if spec.proof else expr_s
        return f"{header}{ns_open}{vars_block}def {name}{params} : SProp := {rhs}\n{ns_close}"

    if kind == "constant":
        return f"{header}{ns_open}{vars_block}constant {name}{params} : SProp\n{ns_close}"

    decl_kw = "axiom" if kind == "axiom" else kind
    proof_part = f" := {spec.proof.strip()}" if spec.proof and kind in ("theorem", "lemma") else ""
    return (
        f"{header}{ns_open}{vars_block}"
        f"constant {name}{params} : SProp\n"
        f"{decl_kw} {name}_def : {name} = ({expr_s}){proof_part}\n"
        f"{ns_close}"
    )
