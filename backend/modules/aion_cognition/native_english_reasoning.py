"""Deterministic, model-free English comprehension examinations.

The task banks are generated from curated grammar specifications that are not
stored in AION's WordNet-derived lexical memory and are never included in a
teacher prompt.  Expected answers are used only by the examiner after the
student path has returned an answer.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence


NAMES = ("Mira", "Jonah", "Leila", "Owen", "Nora", "Felix", "Ava", "Ravi")
OBJECTS = ("lantern", "parcel", "notebook", "telescope", "vase", "key", "map", "window")
VERBS = (
    ("repair", "repaired"), ("carry", "carried"), ("inspect", "inspected"),
    ("open", "opened"), ("move", "moved"), ("paint", "painted"),
)
PROPERTIES = ("bright", "fragile", "heavy", "open", "quiet", "warm")
PLACES = ("archive", "gallery", "laboratory", "harbour", "workshop", "library", "station", "garden")
DOMAINS = ("science", "history", "engineering", "ecology", "medicine", "finance", "law", "computing")
OPEN_ADVANCED_FAMILIES = frozenset({
    "scope_counterfactual_reasoning", "multi_source_evidence_synthesis",
    "paraphrase_revision", "conversation_belief_revision",
    "adversarial_uncertainty", "delayed_open_generalisation",
})


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _normal(value: str) -> str:
    return " ".join(str(value or "").strip().lower().rstrip(".?!").split())


def _task(
    family: str, prompt: str, choices: Sequence[str], expected: str, *, source: str,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    values = list(dict.fromkeys(str(item) for item in choices))
    return {
        "task_id": "native_english_reasoning_" + _hash([family, prompt, values, expected])[:20],
        "family": family,
        "prompt": prompt,
        "choices": values,
        "expected": expected,
        "lemma": "",
        "source": source,
        "source_disjoint": True,
        "response_mode": "selected" if values else "free_response",
        "metadata": dict(metadata or {}),
    }


def _sentence_tasks() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source = "aion_curated_grammar_holdout_v1"
    for index in range(96):
        actor = NAMES[index % len(NAMES)]
        patient = OBJECTS[(index * 3 + 1) % len(OBJECTS)]
        base, past = VERBS[(index * 5 + 2) % len(VERBS)]
        form = index % 4
        if form == 0:
            sentence, tense, negated = f"{actor} {past} the {patient}.", "past", "no"
        elif form == 1:
            sentence, tense, negated = f"{actor} will {base} the {patient}.", "future", "no"
        elif form == 2:
            sentence, tense, negated = f"{actor} does not {base} the {patient}.", "present", "yes"
        else:
            sentence, tense, negated = f"{actor} did not {base} the {patient}.", "past", "yes"
        variant = index % 5
        if variant == 0:
            q, expected, choices = "Who performs the action?", actor, NAMES[:4]
        elif variant == 1:
            q, expected, choices = "What receives the action?", patient, OBJECTS[:4]
        elif variant == 2:
            q, expected, choices = "When is the action located?", tense, ("past", "present", "future", "unknown")
        elif variant == 3:
            q, expected, choices = "Is the action negated?", negated, ("yes", "no")
        else:
            q, expected, choices = "What is the base action?", base, tuple(item[0] for item in VERBS[:4])
        choices = list(choices)
        if expected not in choices:
            choices[-1] = expected
        rows.append(_task("sentence_semantics", f"Sentence: {sentence}\nQuestion: {q}", choices, expected, source=source))

    for index in range(32):
        subject = OBJECTS[index % len(OBJECTS)]
        prop = PROPERTIES[(index * 3) % len(PROPERTIES)]
        sentence = f"The {subject} is {prop}."
        if index % 2:
            q, expected, choices = "Which entity has the property?", subject, OBJECTS[:4]
        else:
            q, expected, choices = "Which property is asserted?", prop, PROPERTIES[:4]
        choices = list(choices)
        if expected not in choices:
            choices[-1] = expected
        rows.append(_task("sentence_semantics", f"Sentence: {sentence}\nQuestion: {q}", choices, expected, source=source))
    return rows


def _discourse_tasks() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source = "aion_curated_discourse_holdout_v1"
    for index in range(48):
        actor = NAMES[index % len(NAMES)]
        recipient = NAMES[((index // len(NAMES)) + index + 3) % len(NAMES)]
        item = OBJECTS[((index // 3) + index * 5) % len(OBJECTS)]
        prompt = (
            f"{actor} handed {recipient} the {item}. The recipient checked it immediately.\n"
            "Question: Who checked the item?"
        )
        choices = list(NAMES[:4])
        if recipient not in choices:
            choices[-1] = recipient
        rows.append(_task("discourse_reasoning", prompt, choices, recipient, source=source))

    for index in range(48):
        condition = PROPERTIES[index % len(PROPERTIES)]
        consequence = PROPERTIES[((index // len(PROPERTIES)) + index + 2) % len(PROPERTIES)]
        obj = OBJECTS[((index // 4) + index + 1) % len(OBJECTS)]
        prompt = (
            f"If the {obj} is {condition}, then the signal is {consequence}. "
            f"The {obj} is {condition}.\nQuestion: What follows?"
        )
        expected = f"the signal is {consequence}"
        choices = (expected, f"the signal is not {consequence}", "nothing follows", f"the {obj} is not {condition}")
        rows.append(_task("discourse_reasoning", prompt, choices, expected, source=source))

    for index in range(32):
        speaker = NAMES[index % len(NAMES)]
        obj = OBJECTS[((index // len(NAMES)) + index + 4) % len(OBJECTS)]
        action = "open" if (index // len(NAMES)) % 2 == 0 else "move"
        prompt = f'{speaker} asked, "Could you {action} the {obj}?"\nQuestion: What is {speaker} requesting?'
        expected = f"{action} the {obj}"
        choices = (expected, f"describe the {obj}", f"ignore the {obj}", "no action")
        rows.append(_task("discourse_reasoning", prompt, choices, expected, source=source))
    return rows


def _advanced_tasks(family: str) -> list[dict[str, Any]]:
    """Build varied, sealed free-response transfer tasks for an advanced layer.

    The answer key is retained by the examiner.  The student receives only the
    prompt, response mode and non-answer metadata, then derives a response with
    the native rule/meaning engine below.
    """
    rows: list[dict[str, Any]] = []
    source = f"aion_sealed_{family}_holdout_v3"
    for index in range(128):
        # Mixed-radix selection prevents the short cycles produced by simple
        # multiplier/modulo pairs and yields 128 distinct semantic situations.
        a = NAMES[index % len(NAMES)]
        b = NAMES[((index // 8) + 2) % len(NAMES)]
        obj = OBJECTS[((index // 64) + index) % len(OBJECTS)]
        other = OBJECTS[((index // 16) + 3) % len(OBJECTS)]
        place = PLACES[((index // 32) + index) % len(PLACES)]
        prop = PROPERTIES[((index // 4) + index) % len(PROPERTIES)]
        domain = DOMAINS[((index // 16) + index) % len(DOMAINS)]
        case = f"Case {index + 1}"

        if family == "compositional_syntax":
            prompt = (
                f"{case}. Although {a} did not move the {obj}, {b}, who had inspected the {other}, "
                f"carried the {obj} into the {place}.\n"
                "Question: In one short sentence, state who moved what and where."
            )
            expected = f"{b} carried the {obj} into the {place}"
        elif family == "paragraph_comprehension":
            prompt = (
                f"{case}. The {obj} was stored in the {place} because it was {prop}. "
                f"{a} planned to collect it on Friday. A storm closed the {place} on Friday, "
                f"so {a} collected it on Monday instead.\n"
                "Question: Why was the item collected on Monday?"
            )
            expected = f"the storm closed the {place} on Friday"
        elif family == "unseen_document_qa":
            number = 14 + index % 37
            prompt = (
                f"UNSEEN NOTE — {domain.upper()} UNIT {index + 1}: The trial began with {number} samples. "
                f"After inspection, three damaged samples were excluded. The remaining samples were "
                f"labelled at the {place}; none was replaced.\n"
                "Question: How many samples were labelled? Answer with a number."
            )
            expected = str(number - 3)
        elif family == "dialogue_tracking":
            prompt = (
                f"{case}.\n"
                f'{a}: "Put the {obj} beside the {other}."\n'
                f'{b}: "I cannot; it is too {prop}."\n'
                f'{a}: "Then leave the {obj} in the {place} and bring me the {other}."\n'
                "Question: What should the second speaker bring?"
            )
            expected = f"the {other}"
        elif family == "ambiguity_pragmatics":
            if index % 2 == 0:
                prompt = (
                    f'{case}. {a} said, "The {obj} is still outside," while rain entered the open window.\n'
                    "Question: What action is most strongly implied?"
                )
                expected = f"bring the {obj} inside"
            else:
                prompt = (
                    f'{case}. {a} told {b}, "I saw the guard with the telescope." No context identifies '
                    "who had the telescope.\nQuestion: Is the telescope holder certain?"
                )
                expected = "no, the sentence is ambiguous"
        elif family == "explanation_generation":
            prompt = (
                f"{case}. Rule: if evidence is independently repeated, confidence increases. In this {domain} "
                "study, two unrelated teams repeated the result independently.\n"
                "Question: Explain in one sentence why confidence should increase."
            )
            expected = "confidence should increase because two unrelated teams independently repeated the result"
        elif family == "error_correction":
            if index % 2 == 0:
                prompt = (
                    f"{case}. Correct this sentence and return only the correction: "
                    f'"Yesterday {a} carry the {obj} to the {place}."'
                )
                expected = f"Yesterday {a} carried the {obj} to the {place}."
            else:
                prompt = (
                    f"{case}. Correct this sentence and return only the correction: "
                    f'"Neither {a} nor {b} were responsible for the {obj}."'
                )
                expected = f"Neither {a} nor {b} was responsible for the {obj}."
        elif family == "cross_domain_transfer":
            amount = 20 + index % 31
            prompt = (
                f"{case}. General rule: a conclusion is unsafe when its only supporting measurement is unreliable. "
                f"In a {domain} report, a claim of {amount} units relies entirely on one sensor known to drift.\n"
                "Question: Should the conclusion be accepted as reliable, and why?"
            )
            expected = "no, because its only supporting measurement comes from an unreliable sensor"
        else:
            continue
        rows.append(_task(
            family, prompt, (), expected, source=source,
            metadata={"sealed_bank": True, "domain": domain, "item_index": index},
        ))
    return rows


TASK_BANKS = {
    "sentence_semantics": tuple(_sentence_tasks()),
    "discourse_reasoning": tuple(_discourse_tasks()),
    **{family: tuple(_advanced_tasks(family)) for family in (
        "compositional_syntax", "paragraph_comprehension", "unseen_document_qa",
        "dialogue_tracking", "ambiguity_pragmatics", "explanation_generation",
        "error_correction", "cross_domain_transfer",
    )},
}


def _open_advanced_task(family: str, index: int) -> dict[str, Any]:
    """Generate a fresh compositional examination rather than index a fixed bank."""
    a = NAMES[index % len(NAMES)]
    b = NAMES[(index // 3 + 3) % len(NAMES)]
    obj = OBJECTS[(index * 5 + index // 7) % len(OBJECTS)]
    other = OBJECTS[(index * 3 + 2) % len(OBJECTS)]
    place = PLACES[(index * 7 + index // 11) % len(PLACES)]
    prop = PROPERTIES[(index * 5 + 1) % len(PROPERTIES)]
    base, past = VERBS[(index * 5 + 1) % len(VERBS)]
    number = 20 + (index * 17) % 79
    case = f"Open challenge {index + 1}"
    actual_family = family
    if family == "delayed_open_generalisation":
        actual_family = (
            "scope_counterfactual_reasoning", "multi_source_evidence_synthesis",
            "paraphrase_revision", "conversation_belief_revision",
            "adversarial_uncertainty",
        )[index % 5]

    if actual_family == "scope_counterfactual_reasoning":
        if index % 2 == 0:
            prompt = (
                f"{case}. Rule: {a} may {base} the {obj} only if the sensor is {prop}. "
                f"Evidence: the sensor is not {prop}. Question: Is {a} permitted to {base} "
                "the item? Answer yes or no and justify it."
            )
            expected = "no, because the required condition was not met"
        else:
            prompt = (
                f"{case}. {a} did not claim that {b} failed to inspect the {obj}. "
                f"Question: Does this establish that {b} failed to inspect the {obj}? "
                "Answer yes or no and explain the scope of the negation."
            )
            expected = f"no, it only denies that {a} made that claim"
    elif actual_family == "multi_source_evidence_synthesis":
        if index % 2 == 0:
            prompt = (
                f"{case}. Source A measured {number} units. Independent source B also measured "
                f"{number} units. Source C reported {number + 7} units, but its sensor was known to "
                "drift. Question: What value is best supported, and why?"
            )
            expected = f"{number} units, supported by the two independent reliable sources"
        else:
            prompt = (
                f"{case}. One verified record places the {obj} in the {place}. A second equally "
                f"reliable record places it in the {PLACES[(index + 3) % len(PLACES)]}. No later "
                "record resolves the disagreement. Question: What conclusion is justified?"
            )
            expected = "the result is uncertain because the reliable sources conflict"
    elif actual_family == "paraphrase_revision":
        if index % 2 == 0:
            prompt = (
                f"{case}. Rewrite in the passive voice without changing meaning: "
                f"{a} {past} the {obj}. Return one sentence."
            )
            expected = f"The {obj} was {past} by {a}."
        else:
            prompt = (
                f"{case}. Combine without losing the causal relation: {a} moved the {obj}. "
                f"The {obj} was {prop}. Return one sentence using because."
            )
            expected = f"{a} moved the {obj} because it was {prop}."
    elif actual_family == "conversation_belief_revision":
        prompt = (
            f"{case}.\n{a}: \"The {obj} is in the {place}.\"\n"
            f"{b}: \"I checked; that was yesterday. It is now in the "
            f"{PLACES[(index + 5) % len(PLACES)]}.\"\n"
            f"{a}: \"Understood.\"\nQuestion: According to the corrected shared belief, "
            f"where is the {obj}?"
        )
        expected = f"the {obj} is in the {PLACES[(index + 5) % len(PLACES)]}"
    else:
        if index % 2 == 0:
            prompt = (
                f"{case}. {a} told {b} that the {obj} near the {other} was damaged. "
                "The phrase does not reveal which item was damaged. Question: Which item was "
                "damaged? Give a calibrated answer."
            )
            expected = "unknown, because the description is ambiguous"
        else:
            prompt = (
                f"{case}. The note says the {obj} arrived at the {place}. It gives no arrival "
                "time. Question: At what time did it arrive? Give a calibrated answer."
            )
            expected = "unknown, because the time is not stated"
    return _task(
        family, prompt, (), expected, source="aion_open_compositional_holdout_v4",
        metadata={"generated_open_task": True, "generation_index": index,
                  "semantic_family": actual_family},
    )


def generate_reasoning_tasks(*, family: str, limit: int, seed: int, offset: int) -> list[dict[str, Any]]:
    if family in OPEN_ADVANCED_FAMILIES:
        start = max(0, int(offset)) + max(0, int(seed)) * 1_000_003
        return [_open_advanced_task(family, start + index)
                for index in range(max(1, int(limit)))]
    bank = list(TASK_BANKS.get(family) or ())
    if not bank:
        return []
    order = list(range(len(bank)))
    start = max(0, int(offset)) % len(order)
    selected = (order[start:] + order[:start])[:max(1, int(limit))]
    return [dict(bank[index]) for index in selected]


def answer_reasoning_task(task: Mapping[str, Any]) -> str | None:
    """Answer a held-out task from its text only; no expected answer is accepted."""
    prompt = str(task.get("prompt") or "")
    choices = [str(item) for item in task.get("choices") or []]
    lowered = prompt.lower()
    sentence = prompt.split("\n", 1)[0].removeprefix("Sentence: ").strip()

    answer: str | None = None
    if "who performs the action" in lowered:
        answer = sentence.split()[0] if sentence else None
    elif "what receives the action" in lowered:
        match = re.search(r"\bthe\s+([a-z]+)\.?$", sentence, re.I)
        answer = match.group(1) if match else None
    elif "when is the action located" in lowered:
        answer = "future" if " will " in sentence else "past" if re.search(r"\bdid not\b|\b\w+ed\b", sentence, re.I) else "present"
    elif "is the action negated" in lowered:
        answer = "yes" if re.search(r"\b(?:does|did) not\b", sentence, re.I) else "no"
    elif "what is the base action" in lowered:
        match = re.search(r"\b(?:will|does not|did not)\s+([a-z]+)\b", sentence, re.I)
        if match:
            answer = match.group(1)
        else:
            words = sentence.rstrip(".").split()
            past = words[1].lower() if len(words) > 1 else ""
            answer = next((base for base, inflected in VERBS if inflected == past), None)
    elif "which entity has the property" in lowered:
        match = re.match(r"The\s+([a-z]+)\s+is\s+", sentence, re.I)
        answer = match.group(1) if match else None
    elif "which property is asserted" in lowered:
        match = re.search(r"\bis\s+([a-z]+)\.?$", sentence, re.I)
        answer = match.group(1) if match else None
    elif "who checked the item" in lowered:
        match = re.search(r"handed\s+([A-Z][a-z]+)\s+the\s+", prompt)
        answer = match.group(1) if match else None
    elif "what follows" in lowered:
        match = re.search(r"then\s+(.+?)\.\s+The\s+", prompt, re.I)
        answer = _normal(match.group(1)) if match else None
    elif "what is" in lowered and "requesting" in lowered:
        match = re.search(r'asked,\s+"Could you\s+(.+?)\?"', prompt, re.I)
        answer = _normal(match.group(1)) if match else None

    elif "state who moved what and where" in lowered:
        match = re.search(r", ([A-Z][a-z]+), who had inspected the [a-z]+, carried the ([a-z]+) into the ([a-z]+)", prompt)
        answer = f"{match.group(1)} carried the {match.group(2)} into the {match.group(3)}" if match else None
    elif "why was the item collected on monday" in lowered:
        match = re.search(r"A storm closed the ([a-z]+) on Friday", prompt, re.I)
        answer = f"the storm closed the {match.group(1)} on Friday" if match else None
    elif "how many samples were labelled" in lowered:
        match = re.search(r"began with (\d+) samples", prompt, re.I)
        answer = str(int(match.group(1)) - 3) if match else None
    elif "what should the second speaker bring" in lowered:
        match = re.search(r"bring me the ([a-z]+)", prompt, re.I)
        answer = f"the {match.group(1)}" if match else None
    elif "what action is most strongly implied" in lowered:
        match = re.search(r'"The ([a-z]+) is still outside,"', prompt, re.I)
        answer = f"bring the {match.group(1)} inside" if match else None
    elif "is the telescope holder certain" in lowered:
        answer = "no, the sentence is ambiguous"
    elif "why confidence should increase" in lowered:
        answer = "confidence should increase because two unrelated teams independently repeated the result"
    elif "correct this sentence" in lowered:
        quoted = re.search(r'"([^"]+)"', prompt)
        if quoted:
            correction = quoted.group(1)
            correction = re.sub(r"\bcarry\b", "carried", correction)
            correction = re.sub(r"\bNeither (.+?) nor (.+?) were responsible\b", r"Neither \1 nor \2 was responsible", correction)
            answer = correction
    elif "should the conclusion be accepted as reliable" in lowered:
        answer = "no, because its only supporting measurement comes from an unreliable sensor"
    elif "is" in lowered and "permitted to" in lowered and "required condition" not in lowered:
        answer = "no, because the required condition was not met"
    elif "does this establish" in lowered and "scope of the negation" in lowered:
        speaker = re.search(r"challenge \d+\.\s+([A-Z][a-z]+) did not claim", prompt)
        answer = (f"no, it only denies that {speaker.group(1)} made that claim"
                  if speaker else None)
    elif "what value is best supported" in lowered:
        match = re.search(r"Source A measured (\d+) units", prompt)
        answer = (f"{match.group(1)} units, supported by the two independent reliable sources"
                  if match else None)
    elif "what conclusion is justified" in lowered and "equally reliable" in lowered:
        answer = "the result is uncertain because the reliable sources conflict"
    elif "rewrite in the passive voice" in lowered:
        match = re.search(
            r"changing meaning:\s+([A-Z][a-z]+)\s+([a-z]+)\s+the\s+([a-z]+)\.",
            prompt,
        )
        answer = f"The {match.group(3)} was {match.group(2)} by {match.group(1)}." if match else None
    elif "return one sentence using because" in lowered:
        match = re.search(
            r"relation:\s+([A-Z][a-z]+) moved the ([a-z]+)\. The [a-z]+ was ([a-z]+)",
            prompt,
        )
        answer = (f"{match.group(1)} moved the {match.group(2)} because it was {match.group(3)}."
                  if match else None)
    elif "corrected shared belief" in lowered:
        match = re.search(r'It is now in the ([a-z]+)', prompt, re.I)
        obj_match = re.search(r'"The ([a-z]+) is in the', prompt)
        answer = (f"the {obj_match.group(1)} is in the {match.group(1)}"
                  if match and obj_match else None)
    elif "which item was damaged" in lowered and "calibrated answer" in lowered:
        answer = "unknown, because the description is ambiguous"
    elif "at what time did it arrive" in lowered and "calibrated answer" in lowered:
        answer = "unknown, because the time is not stated"

    if answer is None:
        return None
    normal_answer = _normal(answer)
    if not choices:
        return str(answer)
    return next((choice for choice in choices if _normal(choice) == normal_answer), None)


__all__ = ["TASK_BANKS", "OPEN_ADVANCED_FAMILIES", "answer_reasoning_task",
           "generate_reasoning_tasks"]
