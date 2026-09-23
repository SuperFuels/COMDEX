"""Cheap, conservative verification for reduced-expert proposal trajectories.

This module does not claim to establish general language-model correctness.
It provides two deliberately narrow gates:

* token-trajectory checks that can reject obvious loops before generation ends;
* deterministic entailment checks for a small, explicitly supported rule form.

Anything outside those gates is sent to a critic or the authoritative model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Iterable, Sequence


@dataclass(frozen=True)
class TrajectoryFailure:
    kind: str
    first_detected_token: int
    detail: str


@dataclass(frozen=True)
class VerificationDecision:
    decision: str
    failures: tuple[TrajectoryFailure, ...]
    derived_conclusions: tuple[str, ...]
    supported_conclusions: tuple[str, ...]
    claim_boundary: str

    def to_dict(self) -> dict:
        value = asdict(self)
        value["failures"] = [asdict(item) for item in self.failures]
        return value


def first_repeated_run(tokens: Sequence[int], *, minimum_run: int = 5) -> TrajectoryFailure | None:
    """Return the earliest implausibly long run of one generated token."""
    if minimum_run < 2:
        raise ValueError("minimum_run must be at least two")
    run = 1
    for index in range(1, len(tokens)):
        if tokens[index] == tokens[index - 1]:
            run += 1
            if run >= minimum_run:
                return TrajectoryFailure(
                    "repeated_token_run", index + 1,
                    f"token {tokens[index]} repeated {minimum_run} times consecutively",
                )
        else:
            run = 1
    return None


def first_repeated_control_token(tokens: Sequence[int]) -> TrajectoryFailure | None:
    """Reject duplicated channel/control markers that cannot form valid output."""
    protected = {200005, 200006, 200007, 200008, 35644}
    for index in range(1, len(tokens)):
        if tokens[index] == tokens[index - 1] and tokens[index] in protected:
            return TrajectoryFailure(
                "repeated_control_token", index + 1,
                f"control/channel token {tokens[index]} repeated consecutively",
            )
    return None


def first_repeated_ngram(
    tokens: Sequence[int], *, n: int = 5, minimum_generated_tokens: int = 16,
    maximum_start_gap: int = 16,
) -> TrajectoryFailure | None:
    """Detect the second occurrence of a repeated local phrase.

    Short repeated phrases are common in correct answers that restate a
    question or emit structured fields.  The default therefore requires five
    exact tokens, non-overlap, and recurrence within a short local span.
    """
    if n < 2:
        raise ValueError("n must be at least two")
    seen: dict[tuple[int, ...], int] = {}
    for end in range(n, len(tokens) + 1):
        gram = tuple(tokens[end - n:end])
        previous = seen.get(gram)
        if (previous is not None and previous + n <= end - n
                and end >= minimum_generated_tokens
                and (end - n) - previous <= maximum_start_gap):
            return TrajectoryFailure(
                "repeated_ngram", end,
                f"{n}-token phrase repeated at generated offsets {previous} and {end - n}",
            )
        seen.setdefault(gram, end - n)
    return None


def trajectory_failures(tokens: Sequence[int]) -> tuple[TrajectoryFailure, ...]:
    failures = [
        first_repeated_control_token(tokens),
        first_repeated_ngram(tokens),
        first_repeated_run(tokens),
    ]
    return tuple(sorted((item for item in failures if item is not None),
                        key=lambda item: (item.first_detected_token, item.kind)))


_EVERY = re.compile(
    r"\bevery\s+(?P<class>[a-z][a-z -]*?)\s+is\s+(?P<predicate>[a-z][a-z -]*?)"
    r"(?=\s+(?:and|but)\b|[.,;?!]|$)", re.IGNORECASE,
)
_SUBJECT_FACT = re.compile(
    r"\b(?P<subject>this\s+[a-z][a-z -]*?)\s+is\s+(?P<predicate>[a-z][a-z -]*?)"
    r"(?=\s+(?:and|but|what|which|can|does)\b|[.,;?!]|$)", re.IGNORECASE,
)


def _normalise_phrase(value: str) -> str:
    return " ".join(value.lower().strip().split())


def derive_simple_entailments(prompt: str) -> tuple[str, ...]:
    """Derive one-hop conclusions from explicit ``every A is B`` rules.

    This is intentionally not a general natural-language theorem prover.  The
    supported grammar is exposed so unsupported requests cannot be accepted by
    accident.
    """
    rules = [
        (_normalise_phrase(match.group("class")),
         _normalise_phrase(match.group("predicate")))
        for match in _EVERY.finditer(prompt)
    ]
    facts = [
        (_normalise_phrase(match.group("subject")),
         _normalise_phrase(match.group("predicate")))
        for match in _SUBJECT_FACT.finditer(prompt)
    ]
    conclusions: set[str] = set()
    for subject, fact in facts:
        subject_noun = subject.split()[-1]
        frontier = [fact]
        visited = {fact}
        while frontier:
            current = frontier.pop()
            for antecedent, consequent in rules:
                implied_class = f"{current} {subject_noun}"
                if antecedent in {current, implied_class} and consequent not in visited:
                    visited.add(consequent)
                    frontier.append(consequent)
                    conclusions.add(f"{subject} is {consequent}")
    return tuple(sorted(conclusions))


def deterministic_entailment_answer(prompt: str) -> str | None:
    """Return a proof-derived answer only when the supported grammar succeeds."""
    conclusions = derive_simple_entailments(prompt)
    if not conclusions:
        return None
    return "; ".join(conclusions).capitalize() + "."


def _conclusion_supported(text: str, conclusion: str) -> bool:
    normalised = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    target = re.sub(r"[^a-z0-9]+", " ", conclusion.lower()).strip()
    return bool(target and re.search(rf"\b{re.escape(target)}\b", normalised))


def verify_candidate(prompt: str, text: str, tokens: Sequence[int]) -> VerificationDecision:
    failures = trajectory_failures(tokens)
    conclusions = derive_simple_entailments(prompt)
    supported = tuple(item for item in conclusions if _conclusion_supported(text, item))
    if failures:
        decision = "ESCALATE"
    elif conclusions and set(supported) == set(conclusions):
        decision = "ACCEPT"
    elif conclusions:
        decision = "ESCALATE"
    else:
        decision = "REQUIRE_CRITIC"
    return VerificationDecision(
        decision=decision,
        failures=failures,
        derived_conclusions=conclusions,
        supported_conclusions=supported,
        claim_boundary=(
            "Structural checks reject obvious loops; deterministic acceptance is limited to "
            "the declared one-hop 'every A is B' grammar. Unsupported tasks require a critic "
            "or authoritative-model escalation."
        ),
    )


def earliest_failure(tokens: Iterable[int]) -> TrajectoryFailure | None:
    """Streaming form used to decide when generation should be interrupted."""
    prefix: list[int] = []
    for token in tokens:
        prefix.append(int(token))
        failures = trajectory_failures(prefix)
        if failures:
            return failures[0]
    return None
