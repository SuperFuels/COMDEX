#!/usr/bin/env python3
"""Governed, Lean-verified memory and repair support for the RH laboratory."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.modules.hexcore.persistent_learning import (
    EvidenceCapsule,
    HexCorePersistentLearningRuntime,
)


def _digest(value: Any) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _allow_verified_math(goal: str) -> Mapping[str, Any]:
    return {
        "allow_learn": goal == "maintain_coherence",
        "deny_reason": None if goal == "maintain_coherence" else "RH_LAB_SCOPE_DENIED",
        "goal": goal,
        "source": "pinned_lean_kernel_and_mathlib",
    }


class AionVerifiedMathMemory:
    """A scoped adapter over AION's durable governed knowledge store."""

    def __init__(self, state_path: Path) -> None:
        self.state_path = Path(state_path)
        self.runtime = HexCorePersistentLearningRuntime(
            state_path=self.state_path,
            authority_provider=_allow_verified_math,
        )

    def ingest_compiler_verified_method(
        self,
        *,
        task_id: str,
        statement: str,
        theorem_signature: str,
        method_pattern: str,
        required_imports: list[str],
        verification: Mapping[str, Any],
        source_uri: str,
    ) -> dict[str, Any]:
        if verification.get("passed") is not True or verification.get("returncode") != 0:
            raise ValueError("only Lean-accepted methods may enter verified memory")
        source_hash = str(verification.get("source_hash") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", source_hash):
            raise ValueError("verified source hash is required")
        method = {
            "task_id": task_id,
            "statement": statement,
            "theorem_signature": theorem_signature,
            "method_pattern": method_pattern,
            "required_imports": list(required_imports),
            "lean_returncode": 0,
            "verified_source_sha256": source_hash,
            "proof_body_retained": False,
        }
        capsule_id = f"rh_lean_{_digest(method)[:20]}"
        capsule = EvidenceCapsule(
            capsule_id=capsule_id,
            source_uri=source_uri,
            content=json.dumps(method, sort_keys=True, ensure_ascii=False),
            claims=[
                {
                    "subject": f"riemann laboratory task {task_id}",
                    "predicate": "has compiler verified Lean method",
                    "object": json.dumps(method, sort_keys=True, ensure_ascii=False),
                    "confidence": 1.0,
                }
            ],
            verified=True,
            confidence=1.0,
        )
        result = self.runtime.knowledge.ingest(capsule)
        if not result.get("accepted"):
            raise RuntimeError(f"verified memory rejected: {result.get('reason')}")
        return {
            "capsule_id": capsule_id,
            "claim_ids": list(result.get("accepted_claim_ids") or []),
            "commit": result.get("commit"),
        }

    def retrieve(self, *, task_id: str, statement: str, limit: int = 3) -> list[dict[str, Any]]:
        query = f"riemann laboratory task {task_id} compiler verified Lean method {statement}"
        accepted: list[dict[str, Any]] = []
        for row in self.runtime.knowledge.retrieve(query, limit=limit):
            claim = dict(row.get("claim") or {})
            evidence = [dict(item) for item in (row.get("evidence") or []) if item]
            if not claim or not evidence or not all(item.get("verified") is True for item in evidence):
                continue
            try:
                method = json.loads(str(claim.get("object") or "{}"))
            except json.JSONDecodeError:
                continue
            if method.get("lean_returncode") != 0 or method.get("proof_body_retained") is not False:
                continue
            accepted.append(
                {
                    "claim_id": claim["claim_id"],
                    "capsule_ids": [item["capsule_id"] for item in evidence],
                    "retrieval_score": row.get("score"),
                    "method": method,
                    "evidence_checksums": [item["checksum"] for item in evidence],
                }
            )
        return accepted


class AionLeanRepairController:
    """Classify Lean failures and produce an auditable bounded repair route."""

    ROUTES = (
        ("unknown_theorem", re.compile(r"unknownIdentifier|unknown identifier", re.I),
         "Search the installed Mathlib catalogue, inspect the exact signature, and replace invented names."),
        ("syntax_failure", re.compile(r"unexpected token|expected command|unknown tactic|invalid syntax", re.I),
         "Correct Lean tactic syntax and return one well-indented tactic body."),
        ("type_mismatch", re.compile(r"type mismatch|application type mismatch|failed to synthesize", re.I),
         "Inspect the goal and theorem types, then correct arguments, coercions, or qualification."),
        ("unsolved_goal", re.compile(r"unsolved goals?|no goals to be solved", re.I),
         "Decompose the remaining goal or apply a verified theorem whose conclusion matches it exactly."),
    )

    def diagnose(self, *, task_id: str, diagnostic: str, attempt: int) -> dict[str, Any]:
        category = "unclassified_failure"
        instruction = "Abandon the failed branch and construct a materially different, minimal proof."
        for route, pattern, guidance in self.ROUTES:
            if pattern.search(diagnostic):
                category, instruction = route, guidance
                break
        record = {
            "task_id": task_id,
            "attempt": attempt,
            "category": category,
            "diagnostic_sha256": hashlib.sha256(diagnostic.encode("utf-8")).hexdigest(),
            "instruction": instruction,
            "max_next_attempts": 1,
        }
        return {**record, "repair_record_id": f"lean_repair_{_digest(record)[:20]}"}


class AionMathlibTheoremDiscovery:
    """Deterministic, read-only search over the pinned Mathlib source tree."""

    STOPWORDS = {
        "a", "and", "at", "be", "by", "exact", "for", "from", "in", "is",
        "of", "on", "or", "prove", "the", "theorem", "this", "to", "using",
    }

    def __init__(self, mathlib_root: Path) -> None:
        self.mathlib_root = Path(mathlib_root)
        self._catalog: list[dict[str, Any]] | None = None

    @classmethod
    def _tokens(cls, value: str) -> set[str]:
        expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
        return {
            token.lower()
            for token in re.findall(r"[A-Za-z][A-Za-z0-9_']+", expanded)
            if token.lower() not in cls.STOPWORDS and len(token) > 2
        }

    def _load_catalog(self) -> list[dict[str, Any]]:
        if self._catalog is not None:
            return self._catalog
        if not self.mathlib_root.exists():
            raise RuntimeError(f"pinned Mathlib source tree is unavailable: {self.mathlib_root}")
        rows: list[dict[str, Any]] = []
        declaration = re.compile(r"^\s*(?:theorem|lemma)\s+([A-Za-z0-9_'.]+)")
        for path in sorted(self.mathlib_root.rglob("*.lean")):
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            for index, line in enumerate(lines):
                match = declaration.match(line)
                if not match:
                    continue
                signature_lines = [line.strip()]
                cursor = index + 1
                while ":=" not in " ".join(signature_lines) and cursor < len(lines) and len(signature_lines) < 12:
                    signature_lines.append(lines[cursor].strip())
                    cursor += 1
                signature = re.sub(r"\s+", " ", " ".join(signature_lines)).split(":=", 1)[0].strip()
                if len(signature) > 1000:
                    continue
                name = match.group(1)
                rows.append({
                    "name": name,
                    "signature": signature,
                    "source": str(path.relative_to(self.mathlib_root)),
                    "line": index + 1,
                    "tokens": self._tokens(name + " " + signature),
                })
        self._catalog = rows
        return rows

    def search(self, *, statement: str, diagnostic: str = "", limit: int = 5) -> list[dict[str, Any]]:
        query_tokens = self._tokens(statement + " " + diagnostic)
        ranked: list[tuple[float, dict[str, Any]]] = []
        for row in self._load_catalog():
            overlap = query_tokens & row["tokens"]
            if not overlap:
                continue
            exact_identifiers = sum(
                1 for token in re.findall(r"[A-Za-z][A-Za-z0-9_']+", statement)
                if token.lower() in row["signature"].lower()
            )
            score = 5.0 * len(overlap) + 2.0 * exact_identifiers
            for marker in (
                "riemannZetaZeros", "riemannZeta", "1 <", "1 ≤", "≠ 0", "= 0",
                "DifferentiableAt", "IsCompact", ".Finite",
            ):
                if marker in statement and marker in row["signature"]:
                    score += 8.0
            if "riemann" in row["source"].lower():
                score += 0.5
            ranked.append((score, row))
        ranked.sort(key=lambda item: (-item[0], item[1]["name"], item[1]["source"], item[1]["line"]))
        results = []
        for score, row in ranked[:limit]:
            public = {key: value for key, value in row.items() if key != "tokens"}
            public["score"] = score
            public["discovery_id"] = f"mathlib_{_digest(public)[:20]}"
            results.append(public)
        return results


def render_theorem_discovery(rows: list[Mapping[str, Any]]) -> str:
    return "\n".join(
        f"- {row['name']}: {row['signature']} [{row['source']}:{row['line']}]"
        for row in rows
    )


def render_verified_memory(rows: list[Mapping[str, Any]]) -> str:
    rendered = []
    for row in rows:
        method = dict(row["method"])
        rendered.append(
            f"- memory_id={row['claim_id']}; imports={method['required_imports']}; "
            f"verified_signature={method['theorem_signature']}; "
            f"method_pattern={method['method_pattern']}; "
            f"evidence_sha256={method['verified_source_sha256']}"
        )
    return "\n".join(rendered)
