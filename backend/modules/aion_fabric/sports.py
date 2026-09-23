from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class LiveSportsInterpreter:
    """Explain sports evidence while separating observation from rule inference."""

    RULES = {
        "offside": "In football, an attacker is generally offside when involved in active play from a position beyond both the ball and the second-last opponent when a teammate plays the ball. Position alone is not an offence.",
        "handball": "A football handball decision depends on deliberate contact or the arm making the body unnaturally bigger, with specific exceptions. Incidental contact is not automatically an offence.",
        "penalty": "A penalty is awarded when a direct-free-kick offence is committed by the defending team inside its own penalty area.",
        "foul": "A foul normally requires prohibited contact or conduct such as tripping, pushing, holding, charging carelessly, or playing dangerously. Broadcast footage may not show the referee's full angle.",
        "yellow card": "A yellow card is a caution. Common reasons include reckless play, dissent, persistent offences, delaying a restart, or stopping a promising attack.",
        "red card": "A red card sends a player off. Common reasons include serious foul play, violent conduct, abusive behaviour, or denying an obvious goal-scoring opportunity in qualifying circumstances.",
        "var": "VAR checks goals, penalties, direct red cards, and mistaken identity for clear and obvious errors or serious missed incidents; the referee remains the final decision-maker.",
        "travel": "In basketball, travelling is illegal movement of the pivot foot or taking too many steps without dribbling after control of the ball.",
        "basketball foul": "A basketball personal foul is illegal contact that disadvantages an opponent; whether contact is incidental depends on position, movement, and the competition rules.",
        "tie break": "A tennis tie-break decides a set at the configured game score. Players usually alternate service after the first point and then every two points; the required winning margin is two points.",
    }

    def __init__(self, runtime_dir: str | Path) -> None:
        self.path = Path(runtime_dir) / "live" / "latest_sports_interpretation.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _bounded_dialogue(live_context: Dict[str, Any], screen: Dict[str, Any]) -> list[str]:
        values = [str(value) for value in list(live_context.get("recent_transcripts") or [])[-4:]]
        values.extend(str(value) for value in list((screen.get("subtitles") or {}).get("lines") or [])[-3:])
        return [" ".join(value.split())[:400] for value in values if value.strip()]

    @classmethod
    def _rule_key(cls, question: str, dialogue: list[str]) -> str | None:
        joined = f"{question} {' '.join(dialogue)}".lower()
        priorities = (
            "yellow card", "red card", "basketball foul", "tie break", "offside",
            "handball", "penalty", "var", "travel", "foul",
        )
        return next((key for key in priorities if key in joined), None)

    @staticmethod
    def _score_answer(scoreboard: Dict[str, Any]) -> tuple[str, Dict[str, Any] | None]:
        score_text = " ".join(str(scoreboard.get("score_text") or "").split())[:180]
        clock = str(scoreboard.get("clock") or "")[:20]
        if not scoreboard.get("detected") or not (score_text or clock):
            return "I do not have a reliable current scoreboard. Capture the television screen and ask again.", None
        parsed = re.search(r"^(.+?)\s+(\d{1,3})\s*[-:]\s*(\d{1,3})\s+(.+)$", score_text)
        structured = None
        if parsed:
            left, left_score, right_score, right = parsed.groups()
            structured = {"left": left, "left_score": int(left_score), "right": right, "right_score": int(right_score)}
            if int(left_score) > int(right_score):
                leader = f"{left} are ahead"
            elif int(right_score) > int(left_score):
                leader = f"{right} are ahead"
            else:
                leader = "the score is level"
            answer = f"The captured scoreboard shows {left} {left_score}, {right} {right_score}; {leader}"
        else:
            answer = f"The captured scoreboard reads {score_text or 'score unavailable'}"
        if clock:
            answer += f", with the clock showing {clock}"
        return answer + ".", structured

    def interpret(
        self,
        *,
        live_context: Dict[str, Any],
        screen_understanding: Dict[str, Any] | None,
        question_kind: str,
        question: str,
    ) -> Dict[str, Any]:
        screen = dict(screen_understanding or {})
        scoreboard = dict(screen.get("scoreboard") or {})
        dialogue = self._bounded_dialogue(live_context, screen)
        rule_key = self._rule_key(question, dialogue)
        score, structured_score = self._score_answer(scoreboard)
        if question_kind in {"score", "leader"}:
            answer = score
            rule = ""
            observed = bool(structured_score or scoreboard.get("clock"))
            confidence = float(scoreboard.get("confidence") or 0) if observed else 0.0
            limitation = "The score comes from the latest owner-captured screen and may become stale as play continues."
        elif rule_key:
            rule = self.RULES[rule_key]
            cue = next((value for value in reversed(dialogue) if rule_key.split()[0] in value.lower()), "")
            if cue:
                answer = f"The observed commentary mentions {rule_key}. The relevant rule is: {rule}"
                confidence = 0.72
                limitation = "Pilot can explain the rule, but cannot verify the referee's view or whether the decision was correct from this evidence alone."
            else:
                answer = f"The relevant rule is: {rule}"
                confidence = 0.58
                limitation = "No reliable incident cue was captured, so this explains the rule without claiming what happened on screen."
            observed = bool(cue)
        else:
            answer = "I did not capture enough evidence to identify that incident. Capture the screen or ask immediately after the commentator names the decision."
            rule = ""
            observed = False
            confidence = 0.0
            limitation = "Pilot will not invent a foul, player, score, or referee decision from an unseen incident."
        record: Dict[str, Any] = {
            "schema_version": "pilot.live-sports.v1",
            "interpretation_id": f"sports_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "question_kind": question_kind,
            "question": " ".join(question.split())[:300],
            "answer": answer[:900],
            "rule_key": rule_key,
            "rule_explanation": rule,
            "observed_incident_cue": observed,
            "scoreboard": {
                "detected": bool(scoreboard.get("detected")),
                "score_text": str(scoreboard.get("score_text") or "")[:180],
                "clock": str(scoreboard.get("clock") or "")[:20],
                "confidence": float(scoreboard.get("confidence") or 0),
                "structured": structured_score,
            },
            "commentary_evidence": dialogue,
            "confidence": round(confidence, 3),
            "limitation": limitation,
            "evidence_boundary": {
                "referee_decision_verified": False,
                "player_identity_inferred": False,
                "public_match_data_used": False,
                "current_screen_capture_required_for_score": True,
            },
            "provider": "aion_deterministic_sports_rules",
            "internet_used": False,
            "paid_ai_used": False,
            "presentation": {"playback_preserved": True, "spoken_summary": True, "private_phone_detail": True},
        }
        record["evidence_hash"] = canonical_hash({"context": live_context.get("context_hash"), "scoreboard": scoreboard, "dialogue": dialogue})
        record["record_hash"] = canonical_hash(record)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(record))
        os.replace(temporary, self.path)
        return record

    def latest(self) -> Dict[str, Any] | None:
        if not self.path.exists():
            return None
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None
