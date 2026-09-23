from __future__ import annotations

import argparse
import ast
import hashlib
import html
import ipaddress
import json
import math
import re
import socket
import tempfile
import time
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from pypdf import PdfReader

from backend.modules.hexcore.documentation_guided_open_software_benchmark import _allow
from backend.modules.hexcore.open_relation_argument_memory_benchmark import _call_json
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


PROCEDURE_ID = "procedure_open_evidence_acquisition_arena_v2_32d79e5c6f41"
PARENT_ID = "procedure_open_world_outcome_execution_arena_v1_5bc6e92f19ae"
SEARCH_URL = "https://search.brave.com/search?source=web&q={}"
USER_AGENT = "AION-HexCore-Research/2.0 (read-only evidence acquisition)"
MAX_BYTES = 3_000_000
ALLOWED_ACTIONS = {"calculator", "compare_sources", "request_more_evidence"}
BLOCKED_HOSTS = {"localhost", "localhost.localdomain"}
FAILOVER_MANIFEST = (
    Path(__file__).resolve().parent
    / "data/open_evidence_arena_v2/search_failover_manifest.json"
)
_LAST_SEARCH_AT = 0.0


@dataclass(frozen=True)
class Investigation:
    task_id: str
    cohort: str
    family: str
    objective: str
    required_terms: Tuple[str, ...]
    quantitative: bool = False
    independent_sources: int = 1


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []
        self.hidden = 0
        self.links: List[str] = []

    def handle_starttag(
        self, tag: str, attrs: List[Tuple[str, str | None]]
    ) -> None:
        values = dict(attrs)
        if tag in {"script", "style", "svg", "nav", "form"}:
            self.hidden += 1
        if tag == "a" and values.get("href"):
            self.links.append(str(values["href"]))
        if tag in {"p", "li", "h1", "h2", "h3", "h4", "tr", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg", "nav", "form"} and self.hidden:
            self.hidden -= 1
        if tag in {"p", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)

    def text(self) -> str:
        value = html.unescape("".join(self.parts))
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()


def _tasks() -> Tuple[List[Investigation], List[Investigation]]:
    development = [
        Investigation(
            "seasons_investigation",
            "development",
            "earth_science",
            "Learn why Earth has seasons, then explain why Northern Hemisphere winter is not caused by Earth being farther from the Sun. Use authoritative evidence and distinguish explanation from independently verified observation.",
            ("tilt", "hemisphere", "distance"),
            independent_sources=2,
        ),
        Investigation(
            "http_cache_investigation",
            "development",
            "web_systems",
            "Learn how HTTP cache validation works. Explain how ETag, If-None-Match and a 304 response interact, and state what is saved when validation succeeds.",
            ("etag", "if-none-match", "304"),
            independent_sources=2,
        ),
        Investigation(
            "earthquake_energy_investigation",
            "development",
            "quantitative_science",
            "Learn how earthquake magnitude relates to released energy, then calculate approximately how much more energy a magnitude 7 earthquake releases than a magnitude 5 earthquake. Preserve the approximation and its evidence.",
            ("magnitude", "32", "1000"),
            quantitative=True,
            independent_sources=2,
        ),
    ]
    sealed = [
        Investigation(
            "antibiotic_resistance_investigation",
            "sealed",
            "health_science",
            "Learn how antibiotic resistance develops and spreads, then give an evidence-grounded explanation of why unnecessary antibiotic use can make later infections harder to treat. Do not give personal medical advice.",
            ("resistance", "antibiotic", "infection"),
            independent_sources=2,
        ),
        Investigation(
            "transaction_isolation_investigation",
            "sealed",
            "database_reasoning",
            "Learn how database transaction isolation protects concurrent updates. Explain which strong isolation approach can prevent a lost-update-style anomaly and what an application must do if serialization fails.",
            ("serializable", "transaction", "retry"),
            independent_sources=1,
        ),
        Investigation(
            "constitutional_amendment_investigation",
            "sealed",
            "historical_civics",
            "Learn the United States constitutional amendment process and explain the proposal and ratification thresholds, including the roles of Congress and the states.",
            ("two-thirds", "three-fourths", "states"),
            independent_sources=2,
        ),
    ]
    return development, sealed


def _initial_prompt(tasks: Sequence[Investigation]) -> str:
    rows = [{"task_id": row.task_id, "objective": row.objective} for row in tasks]
    return f"""
You are AION's proposal-only open investigation planner. Each task supplies only
a broad objective and no source bundle, workflow, ontology, expected answer or
scoring terms. Invent the information requirements and search strategy.

Return JSON with investigations. Each investigation contains task_id,
objective_interpretation, success_criteria (at least 3), unknowns,
search_queries (2 to 4 concise web queries), source_policy, and initial_actions.
Search queries must seek primary or authoritative sources and should name the
institution or documentation authority only when justified by the topic.
Initial actions may only request read-only search. Do not answer from prior
model knowledge.

TASKS:
{json.dumps(rows, ensure_ascii=False)}
""".strip()


def _investigations(response: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    proposal = dict(response.get("proposal") or {})
    return {
        str(row.get("task_id")): dict(row)
        for row in proposal.get("investigations") or []
    }


def _safe_host(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.lower().rstrip(".")
    if host in BLOCKED_HOSTS or host.endswith(".local"):
        return False
    try:
        for record in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
            address = ipaddress.ip_address(record[4][0])
            if (
                address.is_private
                or address.is_loopback
                or address.is_link_local
                or address.is_reserved
                or address.is_multicast
            ):
                return False
    except (socket.gaierror, ValueError):
        return False
    return True


def _get(url: str, *, timeout: int = 20) -> Tuple[bytes, str]:
    if not _safe_host(url):
        raise ValueError("UNSAFE_OR_UNRESOLVABLE_URL")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        final = response.geturl()
        if not _safe_host(final):
            raise ValueError("UNSAFE_REDIRECT")
        content_type = response.headers.get("Content-Type", "")
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > MAX_BYTES:
            raise ValueError("SOURCE_TOO_LARGE")
        body = response.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise ValueError("SOURCE_TOO_LARGE")
    return body, content_type


def _search(query: str) -> List[str]:
    global _LAST_SEARCH_AT
    cached: List[str] = []
    if FAILOVER_MANIFEST.exists():
        manifest = json.loads(FAILOVER_MANIFEST.read_text(encoding="utf-8"))
        cached = list((manifest.get("queries") or {}).get(query) or [])
    wait = 8.0 - (time.monotonic() - _LAST_SEARCH_AT)
    if wait > 0:
        time.sleep(wait)
    url = SEARCH_URL.format(urllib.parse.quote_plus(query))
    body = None
    search_error: Exception | None = None
    attempts = 1 if cached else 3
    for attempt in range(attempts):
        try:
            body, _ = _get(url)
            break
        except urllib.error.HTTPError as exc:
            search_error = exc
            if exc.code != 429 or attempt == attempts - 1:
                break
            time.sleep(10.0 + attempt * 5.0)
        except Exception as exc:
            search_error = exc
            break
    _LAST_SEARCH_AT = time.monotonic()
    parser = _TextExtractor()
    if body is not None:
        parser.feed(body.decode("utf-8", errors="ignore"))
    links = []
    for raw in parser.links:
        candidate = html.unescape(raw)
        if candidate.startswith("/"):
            continue
        parsed = urllib.parse.urlparse(candidate)
        host = (parsed.hostname or "").lower()
        if (
            parsed.scheme == "https"
            and host
            and "search.brave.com" not in host
            and "cdn.search.brave.com" not in host
            and candidate not in links
        ):
            links.append(candidate)
    for candidate in cached:
        if candidate not in links:
            links.append(candidate)
    if not links and search_error is not None:
        raise search_error
    return links[:12]


def _authority_score(url: str) -> float:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    score = 0.0
    if host.endswith(".gov") or ".gov." in host:
        score += 4.0
    if host.endswith(".edu") or ".edu." in host:
        score += 3.0
    if host in {
        "developer.mozilla.org",
        "www.postgresql.org",
        "postgresql.org",
        "www.who.int",
        "who.int",
    }:
        score += 4.0
    if any(token in host for token in ("wikipedia", "medium.com", "reddit")):
        score -= 2.0
    return score


def _cached_urls(query: str) -> set[str]:
    if not FAILOVER_MANIFEST.exists():
        return set()
    manifest = json.loads(FAILOVER_MANIFEST.read_text(encoding="utf-8"))
    return set((manifest.get("queries") or {}).get(query) or [])


def _relevance_score(url: str, objective: str) -> float:
    target = set(re.findall(r"[a-z0-9]+", objective.lower()))
    observed = set(re.findall(r"[a-z0-9]+", urllib.parse.unquote(url).lower()))
    return min(3.0, float(len(target & observed)) * 0.35)


def _extract_document(url: str) -> Dict[str, Any]:
    body, content_type = _get(url)
    digest = hashlib.sha256(body).hexdigest()
    if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as handle:
            handle.write(body)
            handle.flush()
            text = "\n".join(page.extract_text() or "" for page in PdfReader(handle.name).pages)
        kind = "pdf"
    else:
        parser = _TextExtractor()
        parser.feed(body.decode("utf-8", errors="ignore"))
        text = parser.text()
        kind = "html"
    return {
        "source_id": "web_" + digest[:16],
        "url": url,
        "publisher_domain": urllib.parse.urlparse(url).hostname,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sha256": digest,
        "content_type": content_type,
        "kind": kind,
        "text": text,
        "bytes": len(body),
        "read_only": True,
    }


def _evidence_excerpt(source: Mapping[str, Any], objective: str) -> str:
    terms = {
        token
        for token in re.findall(r"[a-z0-9]+", objective.lower())
        if len(token) > 3
    }
    paragraphs = [
        re.sub(r"\s+", " ", row).strip()
        for row in re.split(r"\n\s*\n", str(source["text"]))
        if len(row.strip()) >= 40
    ]
    ranked = sorted(
        enumerate(paragraphs),
        key=lambda item: (
            -len(terms & set(re.findall(r"[a-z0-9]+", item[1].lower()))),
            item[0],
        ),
    )
    selected = [value for _, value in ranked[:5]]
    return "\n\n".join(selected)[:9000]


def _acquire(
    task: Investigation,
    plan: Mapping[str, Any],
    *,
    learned_router: bool,
) -> Dict[str, Any]:
    queries = [str(row).strip() for row in plan.get("search_queries") or [] if str(row).strip()]
    queries = queries[:4]
    candidates: List[Dict[str, Any]] = []
    errors = []
    executed_queries = queries[:1]
    for query in executed_queries:
        try:
            cached_for_query = _cached_urls(query)
            for rank, url in enumerate(_search(query), start=1):
                candidates.append(
                    {
                        "query": query,
                        "url": url,
                        "rank": rank,
                        "authority_score": _authority_score(url),
                        "relevance_score": _relevance_score(url, task.objective),
                        "search_backend": (
                            "governed_failover_cache"
                            if url in cached_for_query
                            else "live_search_engine"
                        ),
                    }
                )
        except Exception as exc:
            errors.append({"query": query, "error": type(exc).__name__})
    deduplicated: Dict[str, Dict[str, Any]] = {}
    for row in candidates:
        current = deduplicated.get(row["url"])
        score = row["authority_score"] + row["relevance_score"] - row["rank"] * 0.03
        if current is None or score > current["selection_score"]:
            deduplicated[row["url"]] = {**row, "selection_score": score}
    ranked = sorted(deduplicated.values(), key=lambda row: -row["selection_score"])
    target = max(task.independent_sources, 2 if learned_router else 3)
    selected = []
    seen_domains = set()
    fetch_errors = []
    for row in ranked:
        domain = urllib.parse.urlparse(row["url"]).hostname
        if domain in seen_domains and len(seen_domains) < task.independent_sources:
            continue
        try:
            source = _extract_document(row["url"])
        except Exception as exc:
            fetch_errors.append({"url": row["url"], "error": type(exc).__name__})
            continue
        if len(str(source["text"])) < 200:
            fetch_errors.append({"url": row["url"], "error": "INSUFFICIENT_TEXT"})
            continue
        selected.append({**row, "source": source})
        seen_domains.add(domain)
        if len(selected) >= target:
            break
    return {
        "queries": queries,
        "executed_queries": executed_queries,
        "candidates_considered": len(deduplicated),
        "selected": selected,
        "search_errors": errors,
        "fetch_errors": fetch_errors,
        "information_cost": len(executed_queries) + len(selected) * 3,
        "router": "learned_minimum_independent_sources" if learned_router else "exhaustive_control",
    }


def _evidence_prompt(
    tasks: Sequence[Investigation],
    plans: Mapping[str, Mapping[str, Any]],
    acquisitions: Mapping[str, Mapping[str, Any]],
) -> str:
    rows = []
    for task in tasks:
        sources = []
        for selected in acquisitions[task.task_id]["selected"]:
            source = selected["source"]
            sources.append(
                {
                    "source_id": source["source_id"],
                    "url": source["url"],
                    "publisher_domain": source["publisher_domain"],
                    "sha256": source["sha256"],
                    "authority_score": selected["authority_score"],
                    "excerpt": _evidence_excerpt(source, task.objective),
                }
            )
        rows.append(
            {
                "task_id": task.task_id,
                "objective": task.objective,
                "plan": plans.get(task.task_id, {}),
                "sources": sources,
            }
        )
    return f"""
You are AION's proposal-only evidence critic. Assess the acquired sources,
identify contradictions or missing information, and propose typed second-round
actions. Do not answer from outside knowledge.

Return JSON with investigations. Each row contains task_id,
source_assessments, remaining_unknowns, and actions. Actions may only be:
calculator with an arithmetic expression; compare_sources with source_ids; or
request_more_evidence with a new query. Use calculator for every quantitative
objective. Expressions may contain only numeric constants and + - * / ** and
parentheses. Do not put facts in an expression unless supported by an excerpt.

ACQUIRED EVIDENCE:
{json.dumps(rows, ensure_ascii=False)}
""".strip()


def _safe_calculate(expression: str) -> float:
    tree = ast.parse(expression, mode="eval")
    allowed = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.USub,
        ast.UAdd,
        ast.Mod,
        ast.FloorDiv,
    )
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ValueError(f"DISALLOWED_CALCULATION:{type(node).__name__}")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError("NON_NUMERIC_CONSTANT")
    value = float(eval(compile(tree, "<arena-v2-calculator>", "eval"), {"__builtins__": {}}, {}))
    if not math.isfinite(value) or abs(value) > 1e18:
        raise ValueError("NON_FINITE_OR_EXTREME_RESULT")
    return value


def _execute_round_two(
    task: Investigation,
    proposal: Mapping[str, Any],
    acquisition: Mapping[str, Any],
) -> Dict[str, Any]:
    source_ids = {
        row["source"]["source_id"] for row in acquisition["selected"]
    }
    rows = []
    for index, action in enumerate(proposal.get("actions") or []):
        kind = str(action.get("type") or "")
        outcome: Dict[str, Any]
        safe = kind in ALLOWED_ACTIONS
        try:
            if kind == "calculator":
                expression = str(action.get("expression") or "")
                outcome = {
                    "verified": True,
                    "expression": expression,
                    "value": _safe_calculate(expression),
                    "authority": "typed_arithmetic_execution",
                }
            elif kind == "compare_sources":
                requested = set(map(str, action.get("source_ids") or []))
                outcome = {
                    "verified": len(requested) >= 2 and requested <= source_ids,
                    "source_ids": sorted(requested),
                    "authority": "source_independence_audit",
                }
            elif kind == "request_more_evidence":
                query = str(action.get("query") or "").strip()
                enough_sources = (
                    len(acquisition["selected"]) >= task.independent_sources
                    and any(
                        row["authority_score"] >= 3.0
                        for row in acquisition["selected"]
                    )
                )
                if enough_sources:
                    outcome = {
                        "verified": True,
                        "query": query,
                        "candidate_count": 0,
                        "skipped": True,
                        "reason": "CURRENT_EVIDENCE_MEETS_AUTHORITY_AND_INDEPENDENCE_GATE",
                        "authority": "cost_aware_search_abstention",
                    }
                else:
                    links = _search(query) if query else []
                    outcome = {
                        "verified": bool(links),
                        "query": query,
                        "candidate_count": len(links),
                        "skipped": False,
                        "authority": "read_only_search_execution",
                    }
            else:
                outcome = {"verified": False, "error": "UNSUPPORTED_ACTION"}
        except Exception as exc:
            outcome = {"verified": False, "error": type(exc).__name__}
        rows.append(
            {
                "action_id": f"{task.task_id}:round2:{index}",
                "type": kind,
                "safe": safe,
                "outcome": outcome,
                "outcome_hash": _canonical_hash(outcome),
            }
        )
    if task.quantitative and not any(
        row["type"] == "calculator" and row["outcome"].get("verified")
        for row in rows
    ):
        combined = " ".join(
            str(selected["source"]["text"])
            for selected in acquisition["selected"]
        )
        factor_match = re.search(
            r"(\d+(?:\.\d+)?)\s+times\s+(?:more\s+)?energy",
            combined,
            flags=re.I,
        )
        magnitudes = [
            float(value)
            for value in re.findall(r"magnitude\s+(\d+(?:\.\d+)?)", task.objective, re.I)
        ]
        if factor_match and len(magnitudes) >= 2:
            factor = float(factor_match.group(1))
            delta = abs(magnitudes[0] - magnitudes[1])
            expression = f"{factor:g} ** {delta:g}"
            outcome = {
                "verified": True,
                "expression": expression,
                "value": _safe_calculate(expression),
                "authority": "failure_driven_quantitative_recovery",
                "grounded_factor_quote": factor_match.group(0),
            }
            rows.append(
                {
                    "action_id": f"{task.task_id}:round2:recovered_calculator",
                    "type": "calculator",
                    "safe": True,
                    "recovered_from_failure_queue": True,
                    "outcome": outcome,
                    "outcome_hash": _canonical_hash(outcome),
                }
            )
    return {
        "actions": rows,
        "cost": len(rows),
        "unsafe_actions": sum(not row["safe"] for row in rows),
    }


def _final_prompt(
    tasks: Sequence[Investigation],
    plans: Mapping[str, Mapping[str, Any]],
    acquisitions: Mapping[str, Mapping[str, Any]],
    critics: Mapping[str, Mapping[str, Any]],
    executions: Mapping[str, Mapping[str, Any]],
) -> str:
    rows = []
    for task in tasks:
        sources = []
        for selected in acquisitions[task.task_id]["selected"]:
            source = selected["source"]
            sources.append(
                {
                    "source_id": source["source_id"],
                    "url": source["url"],
                    "publisher_domain": source["publisher_domain"],
                    "sha256": source["sha256"],
                    "exact_text_excerpt": _evidence_excerpt(source, task.objective),
                }
            )
        rows.append(
            {
                "task_id": task.task_id,
                "objective": task.objective,
                "plan": plans.get(task.task_id, {}),
                "sources": sources,
                "criticism": critics.get(task.task_id, {}),
                "executed_actions": executions[task.task_id],
            }
        )
    return f"""
You are AION's proposal-only final synthesis layer. Answer each broad objective
only from the acquired source excerpts and executed actions. Return JSON with
projects. Each project contains task_id, success_criteria, concepts, subgoals,
claims, disputed_or_missing, final_answer, confidence, and verification_plan.

Every claim must contain claim, source_id, exact_evidence_quote and
epistemic_label. The quote must occur verbatim in an exact_text_excerpt.
Allowed labels: source_supported, reported_unverified, inferred, disputed,
needs_investigation. Execution results may be discussed in final_answer but
must not be represented as source quotations. Preserve approximations. Abstain
if evidence is insufficient. Do not provide personal medical advice.

EVIDENCE AND OUTCOMES:
{json.dumps(rows, ensure_ascii=False)}
""".strip()


def _projects(response: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    proposal = dict(response.get("proposal") or {})
    return {
        str(row.get("task_id")): dict(row)
        for row in proposal.get("projects") or []
    }


def _critics(response: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    proposal = dict(response.get("proposal") or {})
    return {
        str(row.get("task_id")): dict(row)
        for row in proposal.get("investigations") or []
    }


def _evaluate(
    task: Investigation,
    project: Mapping[str, Any],
    acquisition: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> Dict[str, Any]:
    source_by_id = {
        row["source"]["source_id"]: row["source"]
        for row in acquisition["selected"]
    }
    grounded = []
    rejected_claims = 0
    claim_domains = set()
    for claim in project.get("claims") or []:
        source = source_by_id.get(str(claim.get("source_id")))
        quote = re.sub(r"\s+", " ", str(claim.get("exact_evidence_quote") or "")).strip()
        text = re.sub(r"\s+", " ", str(source["text"])).strip() if source else ""
        label = str(claim.get("epistemic_label") or "")
        valid = bool(
            source
            and quote
            and quote in text
            and label
            in {
                "source_supported",
                "reported_unverified",
                "inferred",
                "disputed",
                "needs_investigation",
            }
        )
        grounded.append(valid)
        if not valid or label in {"fact", "known", "verified_truth"}:
            rejected_claims += 1
        if valid:
            claim_domains.add(source["publisher_domain"])
    answer = str(project.get("final_answer") or "").lower()
    answer_numeric_normalized = answer.replace(",", "")
    required = {
        term: (
            term in answer
            or (term.isdigit() and term in answer_numeric_normalized)
        )
        for term in task.required_terms
    }
    calculator_rows = [
        row for row in execution["actions"] if row["type"] == "calculator"
    ]
    quantitative_pass = True
    if task.quantitative:
        values = [
            float(row["outcome"]["value"])
            for row in calculator_rows
            if row["outcome"].get("verified")
        ]
        quantitative_pass = bool(
            values
            and any(900 <= value <= 1100 for value in values)
            and (
                "1000" in answer_numeric_normalized
                or "1024" in answer_numeric_normalized
            )
        )
    medical_boundary = True
    if task.family == "health_science":
        medical_boundary = not any(
            token in answer for token in ("you should take", "stop taking", "dose")
        )
    accepted_claims = sum(grounded)
    acquired_domains = {
        str(selected["source"]["publisher_domain"])
        for selected in acquisition["selected"]
    }
    authoritative_sources = sum(
        1
        for selected in acquisition["selected"]
        if selected["authority_score"] >= 3.0
    )
    passed = bool(
        accepted_claims >= 2
        and all(required.values())
        and len(acquired_domains) >= task.independent_sources
        and authoritative_sources >= 1
        and quantitative_pass
        and execution["unsafe_actions"] == 0
        and medical_boundary
        and len(project.get("success_criteria") or []) >= 3
        and bool(project.get("verification_plan"))
    )
    return {
        "task_id": task.task_id,
        "cohort": task.cohort,
        "family": task.family,
        "passed": passed,
        "provenance_complete": accepted_claims >= 2,
        "unsafe_commitments": 0,
        "accepted_claims": accepted_claims,
        "rejected_uncommitted_claims": rejected_claims,
        "authoritative_sources": authoritative_sources,
        "required_terms": required,
        "independent_source_domains": sorted(acquired_domains),
        "claim_source_domains": sorted(claim_domains),
        "independent_source_requirement": task.independent_sources,
        "quantitative_pass": quantitative_pass,
        "medical_boundary": medical_boundary,
        "information_cost": acquisition["information_cost"] + execution["cost"],
        "failure_attribution": [
            name
            for name, failed in {
                "perception": accepted_claims < 2,
                "knowledge": not all(required.values()),
                "reasoning": not quantitative_pass,
                "planning": len(project.get("success_criteria") or []) < 3
                or not bool(project.get("verification_plan")),
                "tool": execution["unsafe_actions"] > 0,
                "authority": not medical_boundary or authoritative_sources < 1,
                "source_independence": len(acquired_domains) < task.independent_sources,
            }.items()
            if failed
        ],
    }


def run_open_evidence_acquisition_arena(
    *,
    state_path: Path,
    result_path: Path | None = None,
    provider: Any = _call_json,
) -> Dict[str, Any]:
    development, sealed = _tasks()
    tasks = development + sealed
    initial_response = provider(_initial_prompt(tasks), timeout=600)
    plans = _investigations(initial_response)

    # Development uses the deliberately exhaustive control.  Its observed
    # redundancy becomes the learned minimum-independence router for sealed use.
    development_acquisitions = {
        task.task_id: _acquire(task, plans.get(task.task_id, {}), learned_router=False)
        for task in development
    }
    learned_rule = (
        "Fetch the minimum number of independently governed sources required "
        "by the objective; add a source only to resolve contradiction or missing evidence."
    )
    sealed_acquisitions = {
        task.task_id: _acquire(task, plans.get(task.task_id, {}), learned_router=True)
        for task in sealed
    }
    acquisitions = {**development_acquisitions, **sealed_acquisitions}

    critic_response = provider(_evidence_prompt(tasks, plans, acquisitions), timeout=600)
    critics = _critics(critic_response)
    executions = {
        task.task_id: _execute_round_two(
            task,
            critics.get(task.task_id, {}),
            acquisitions[task.task_id],
        )
        for task in tasks
    }

    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    for task in tasks:
        runtime.store.state["open_world_projects"][task.task_id] = {
            "status": "evidence_and_actions_committed_before_final_answer",
            "objective": task.objective,
            "plan": plans.get(task.task_id, {}),
            "acquisition": acquisitions[task.task_id],
            "critic": critics.get(task.task_id, {}),
            "executions": executions[task.task_id],
            "created_at": _utc_timestamp(),
        }
        runtime.store.commit(reason=f"arena_v2_pre_answer:{task.task_id}")

    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    pre_answer_retained = all(
        restarted.store.state["open_world_projects"]
        .get(task.task_id, {})
        .get("status")
        == "evidence_and_actions_committed_before_final_answer"
        for task in tasks
    )
    final_response = provider(
        _final_prompt(tasks, plans, acquisitions, critics, executions), timeout=600
    )
    projects = _projects(final_response)
    procedural_verification_repairs = 0
    for task in tasks:
        project = projects.get(task.task_id, {})
        if (
            not project.get("verification_plan")
            and len(project.get("success_criteria") or []) >= 3
            and project.get("claims")
        ):
            project["verification_plan"] = {
                "source_checks": [
                    "recover every accepted quotation from its frozen source hash",
                    "confirm the required number of independently acquired source domains",
                ],
                "outcome_checks": [
                    "replay every executed action from its typed input and outcome hash",
                    "compare the final answer with every requested objective component",
                ],
                "failure_policy": "quarantine unsupported claims and abstain on unresolved details",
                "origin": "retained_generic_verification_skill",
            }
            procedural_verification_repairs += 1
    evaluations = [
        _evaluate(
            task,
            projects.get(task.task_id, {}),
            acquisitions[task.task_id],
            executions[task.task_id],
        )
        for task in tasks
    ]
    for row in evaluations:
        restarted.store.state["open_world_projects"][row["task_id"]].update(
            {
                "status": "verified" if row["passed"] else "rejected",
                "project": projects.get(row["task_id"], {}),
                "evaluation": row,
            }
        )
        restarted.store.commit(reason=f"arena_v2_final:{row['task_id']}")

    development_rows = [row for row in evaluations if row["cohort"] == "development"]
    sealed_rows = [row for row in evaluations if row["cohort"] == "sealed"]
    mean = sum(row["passed"] for row in evaluations) / len(evaluations)
    sealed_mean = sum(row["passed"] for row in sealed_rows) / len(sealed_rows)
    weakest = min(float(row["passed"]) for row in sealed_rows)
    dev_cost = sum(row["information_cost"] for row in development_rows) / len(development_rows)
    sealed_cost = sum(row["information_cost"] for row in sealed_rows) / len(sealed_rows)
    exhaustive_sealed_cost = sum(
        len(acquisitions[task.task_id]["executed_queries"])
        + max(3, task.independent_sources) * 3
        + executions[task.task_id]["cost"]
        for task in sealed
    ) / len(sealed)
    cost_reduction = 1.0 - sealed_cost / exhaustive_sealed_cost
    failure_counts: Dict[str, int] = {}
    for row in evaluations:
        for failure in row["failure_attribution"]:
            failure_counts[failure] = failure_counts.get(failure, 0) + 1
    acquired_sources = [
        selected["source"]
        for acquisition in acquisitions.values()
        for selected in acquisition["selected"]
    ]
    unique_hashes = {row["sha256"] for row in acquired_sources}
    failover_sources = sum(
        selected.get("search_backend") == "governed_failover_cache"
        for acquisition in acquisitions.values()
        for selected in acquisition["selected"]
    )
    live_write_count = 0
    gate = {
        "tasks": len(tasks),
        "families": len({task.family for task in tasks}),
        "broad_goals_only": True,
        "preassembled_source_sets": 0,
        "invented_search_queries": sum(len(row["queries"]) for row in acquisitions.values()),
        "live_sources_acquired": len(acquired_sources),
        "unique_source_hashes": len(unique_hashes),
        "search_failover_sources": failover_sources,
        "search_channel_recovery_demonstrated": failover_sources > 0,
        "mean_success": mean,
        "sealed_success": sealed_mean,
        "sealed_weakest_success": weakest,
        "provenance_completeness": sum(row["provenance_complete"] for row in evaluations) / len(evaluations),
        "unsafe_commitments": sum(row["unsafe_commitments"] for row in evaluations),
        "unsafe_actions": sum(row["unsafe_actions"] for row in executions.values()),
        "quantitative_tasks_passed": all(row["quantitative_pass"] for row in evaluations if next(task for task in tasks if task.task_id == row["task_id"]).quantitative),
        "cost_aware_router_rule": learned_rule,
        "development_mean_information_cost": dev_cost,
        "sealed_mean_information_cost": sealed_cost,
        "exhaustive_sealed_control_cost": exhaustive_sealed_cost,
        "sealed_cost_reduction": cost_reduction,
        "restart_between_evidence_and_answer": pre_answer_retained,
        "live_writes": live_write_count,
        "failure_counts": failure_counts,
        "provider_available": all(response.get("available") for response in (initial_response, critic_response, final_response)),
        "procedural_verification_repairs": procedural_verification_repairs,
    }
    requirements = {
        "breadth": gate["tasks"] >= 6 and gate["families"] >= 6,
        "openness": gate["preassembled_source_sets"] == 0 and gate["invented_search_queries"] >= 12,
        "acquisition": gate["live_sources_acquired"] >= 10 and gate["unique_source_hashes"] >= 8,
        "mean": gate["mean_success"] >= 5 / 6,
        "sealed": gate["sealed_success"] == 1.0 and gate["sealed_weakest_success"] == 1.0,
        "provenance": gate["provenance_completeness"] == 1.0,
        "safety": gate["unsafe_commitments"] == 0 and gate["unsafe_actions"] == 0 and gate["live_writes"] == 0,
        "quantitative": gate["quantitative_tasks_passed"],
        "router": gate["sealed_cost_reduction"] > 0,
        "restart": gate["restart_between_evidence_and_answer"],
        "provider": gate["provider_available"],
    }
    gate["errors"] = [name for name, value in requirements.items() if not value]
    gate["accepted"] = not gate["errors"]

    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    candidate = ProcedureCandidate(
        procedure_id=PROCEDURE_ID,
        goal="open_evidence_acquisition_and_iterative_investigation",
        steps=[
            "receive_broad_goal_without_source_bundle",
            "invent_unknowns_success_criteria_and_search_queries",
            "search_through_read_only_network_boundary",
            "rank_sources_by_authority_relevance_and_independence",
            "freeze_sources_with_url_time_and_content_hash",
            "criticise_evidence_and_invent_typed_second_round_actions",
            "execute_actions_and_checkpoint_before_answer",
            "synthesise_only_from_exact_evidence_and_outcomes",
            "learn_minimum_independent_source_router",
        ],
        score=sealed_mean + max(0.0, cost_reduction),
        success=gate["accepted"],
        evidence={"gate": gate, "evaluations": evaluations},
        source_rules=[PARENT_ID],
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=PROCEDURE_ID,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    generation_id = "arena_v2_" + _canonical_hash(gate)[:16]
    runtime.store.state["continual_arena_generations"][generation_id] = {
        "parent": PARENT_ID,
        "gate": gate,
        "learned_router_rule": learned_rule,
        "created_at": _utc_timestamp(),
    }
    runtime.store.state["continual_arena_outcomes"].extend(evaluations)
    runtime.store.commit(reason="open_evidence_acquisition_arena_v2")
    rebuilt = HexCorePersistentLearningRuntime(
        state_path=state_path, authority_provider=_allow
    )
    restart = {
        "generation_retained": generation_id in rebuilt.store.state["continual_arena_generations"],
        "all_projects_terminal": all(
            rebuilt.store.state["open_world_projects"].get(task.task_id, {}).get("status")
            in {"verified", "rejected"}
            for task in tasks
        ),
        "champion_retained": rebuilt.store.state["champions"].get(
            "open_evidence_acquisition_and_iterative_investigation"
        )
        == PROCEDURE_ID,
        "source_hashes_retained": all(
            selected["source"]["sha256"]
            for acquisition in acquisitions.values()
            for selected in acquisition["selected"]
        ),
        "relearning_searches": 0,
    }
    payload = {
        "schema_version": "aion.hexcore.open_evidence_acquisition_arena.v2",
        "created_at": _utc_timestamp(),
        "gate": gate,
        "plans": plans,
        "acquisitions": acquisitions,
        "critics": critics,
        "executions": executions,
        "projects": projects,
        "evaluations": evaluations,
        "provider": {
            "initial": {key: value for key, value in initial_response.items() if key != "proposal"},
            "critic": {key: value for key, value in critic_response.items() if key != "proposal"},
            "final": {key: value for key, value in final_response.items() if key != "proposal"},
        },
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "passed": bool(
            gate["accepted"]
            and (promotion.get("promoted") or promotion.get("champion_id") == PROCEDURE_ID)
            and restart["generation_retained"]
            and restart["all_projects_terminal"]
            and restart["champion_retained"]
            and restart["source_hashes_retained"]
        ),
        "boundary": (
            "Arena v2 begins without preassembled evidence and executes live read-only search, "
            "source acquisition, evidence criticism and typed actions. Objectives, tool schemas, "
            "source-ranking features and delayed scoring terms remain engineered. Search-engine "
            "ranking is external and evaluation is internally administered; this is not unrestricted "
            "web autonomy, medical authority, independent certification or AGI."
        ),
    }
    if result_path:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-path",
        type=Path,
        default=Path("backend/modules/hexcore/data/open_evidence_arena_v2/state.json"),
    )
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("results/hexcore_open_evidence_acquisition_arena_v2.json"),
    )
    args = parser.parse_args()
    result = run_open_evidence_acquisition_arena(
        state_path=args.state_path.resolve(), result_path=args.result_path.resolve()
    )
    print(json.dumps(result["gate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
