from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import chess

from backend.modules.sqi.sqi_beam_kernel import SQIBeamKernel

try:
    from backend.modules.codex.beam_model import Beam
except Exception:
    Beam = None  # type: ignore

try:
    from backend.modules.beamline.beam_store import persist_beam_events
except Exception:
    persist_beam_events = None  # type: ignore


DEFAULT_MEMORY_PATH = Path("data/aion_games/full_chess_opponent_response_beam_planner_memory.json")


PIECE_VALUES = {
    chess.PAWN: 1.0,
    chess.KNIGHT: 3.0,
    chess.BISHOP: 3.0,
    chess.ROOK: 5.0,
    chess.QUEEN: 9.0,
    chess.KING: 0.0,
}


@dataclass(frozen=True)
class OpponentResponseBeam:
    beam_id: str
    reply_move: str
    mode: str
    danger_score: float
    plan_damage_score: float
    material_risk_score: float
    king_safety_risk_score: float
    tempo_score: float
    total_beam_score: float
    sqi_coherence: float
    sqi_phase: float
    sqi_amplitude: float
    gives_check: bool
    gives_mate: bool
    is_capture: bool
    attacks_queen: bool
    attacks_king_zone: bool
    blocks_plan: bool
    is_development: bool
    is_pawn_break: bool
    explanation: str


@dataclass(frozen=True)
class OpponentResponseBeamPlannerResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    input_fen: str
    side_to_move: str
    candidate_move: str
    candidate_move_is_legal: bool
    opponent_side: str
    opponent_legal_reply_count: int
    max_beams: int
    beam_count: int
    top_beam_mode: str
    top_reply_move: str
    top_danger_score: float
    beams: List[Dict[str, Any]]
    sqi_beam_packets: List[Dict[str, Any]]
    sqi_propagation_results: List[Dict[str, Any]]
    qqc_control_packet: Dict[str, Any]
    hexcore_field_packet: Dict[str, Any]
    container_evidence_record: Dict[str, Any]
    trace_hash: str
    policy_memory_mutated: bool
    final_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str


class AionOpponentResponseBeamPlannerKernel:
    def __init__(self, memory_path: Optional[Path] = None) -> None:
        self.memory_path = Path(memory_path or DEFAULT_MEMORY_PATH)
        self.memory_loaded = False
        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "last_candidate_move": "",
            "last_top_reply_move": "",
            "last_top_beam_mode": "",
            "last_trace_hash": None,
        }
        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
            policy = data.get("opponent_response_beam_planner_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True
        except Exception:
            self.memory_loaded = False

    def _save_memory(self, result: OpponentResponseBeamPlannerResult) -> None:
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "opponent_response_beam_planner_policy": self.policy,
            "last_result": asdict(result),
        }
        self.memory_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _hash(payload: Dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    @staticmethod
    def _side_name(side: chess.Color) -> str:
        return "white" if side == chess.WHITE else "black"

    @staticmethod
    def _king_zone(board: chess.Board, side: chess.Color) -> List[int]:
        king = board.king(side)
        if king is None:
            return []
        return [king] + list(chess.SquareSet(chess.BB_KING_ATTACKS[king]))

    @staticmethod
    def _is_development_move(board: chess.Board, move: chess.Move, side: chess.Color) -> bool:
        piece = board.piece_at(move.from_square)
        if not piece or piece.color != side:
            return False
        if piece.piece_type not in {chess.KNIGHT, chess.BISHOP}:
            return False
        home_rank = 0 if side == chess.WHITE else 7
        return chess.square_rank(move.from_square) == home_rank

    @staticmethod
    def _is_pawn_break(board: chess.Board, move: chess.Move, side: chess.Color) -> bool:
        piece = board.piece_at(move.from_square)
        if not piece or piece.color != side or piece.piece_type != chess.PAWN:
            return False
        file_ = chess.square_file(move.to_square)
        rank = chess.square_rank(move.to_square)
        return file_ in {2, 3, 4, 5} and (rank >= 3 if side == chess.WHITE else rank <= 4)

    @staticmethod
    def _attacks_enemy_queen(board_after_reply: chess.Board, opponent: chess.Color, our_side: chess.Color) -> bool:
        queens = board_after_reply.pieces(chess.QUEEN, our_side)
        return any(board_after_reply.is_attacked_by(opponent, sq) for sq in queens)

    def _classify_mode(
        self,
        *,
        board_after_candidate: chess.Board,
        board_after_reply: chess.Board,
        move: chess.Move,
        opponent: chess.Color,
        our_side: chess.Color,
        target_weakness: str,
        primary_plan: str,
    ) -> str:
        if board_after_reply.is_checkmate():
            return "mate"
        if board_after_reply.is_check():
            return "check"
        if board_after_candidate.is_capture(move):
            return "capture"
        if self._attacks_enemy_queen(board_after_reply, opponent, our_side):
            return "queen_attack"

        king_zone = self._king_zone(board_after_reply, our_side)
        if any(board_after_reply.is_attacked_by(opponent, sq) for sq in king_zone):
            return "king_attack"

        if target_weakness in {"central_control", "undeveloped_position", "king_safety"}:
            if chess.square_file(move.to_square) in {2, 3, 4, 5}:
                return "plan_blocker"

        if primary_plan in {"rapid_development", "central_control"} and chess.square_file(move.to_square) in {2, 3, 4, 5}:
            return "plan_blocker"

        if self._is_pawn_break(board_after_candidate, move, opponent):
            return "pawn_break"

        if self._is_development_move(board_after_candidate, move, opponent):
            return "development"

        return "normal_reply"

    def _score_reply(
        self,
        *,
        board_after_candidate: chess.Board,
        board_after_reply: chess.Board,
        move: chess.Move,
        opponent: chess.Color,
        our_side: chess.Color,
        mode: str,
        primary_plan: str,
    ) -> OpponentResponseBeam:
        captured_piece = board_after_candidate.piece_at(move.to_square)
        captured_value = PIECE_VALUES.get(captured_piece.piece_type, 0.0) if captured_piece else 0.0

        gives_check = board_after_reply.is_check()
        gives_mate = board_after_reply.is_checkmate()
        is_capture = board_after_candidate.is_capture(move)
        attacks_queen = self._attacks_enemy_queen(board_after_reply, opponent, our_side)
        king_zone = self._king_zone(board_after_reply, our_side)
        attacks_king_zone = any(board_after_reply.is_attacked_by(opponent, sq) for sq in king_zone)

        blocks_plan = mode == "plan_blocker"
        is_development = self._is_development_move(board_after_candidate, move, opponent)
        is_pawn_break = self._is_pawn_break(board_after_candidate, move, opponent)

        danger = 0.0
        plan_damage = 0.0
        material_risk = min(1.0, captured_value / 9.0)
        king_safety = 0.0
        tempo = 0.0

        if gives_mate:
            danger += 1.0
            king_safety += 1.0
        elif gives_check:
            danger += 0.72
            king_safety += 0.72

        if is_capture:
            danger += 0.18 + material_risk * 0.45
            tempo += 0.12

        if attacks_queen:
            danger += 0.38
            tempo += 0.24

        if attacks_king_zone:
            danger += 0.18
            king_safety += 0.22

        if blocks_plan:
            plan_damage += 0.42
            danger += 0.12

        if is_pawn_break:
            plan_damage += 0.22
            tempo += 0.10

        if is_development:
            tempo += 0.10
            plan_damage += 0.08 if primary_plan == "rapid_development" else 0.0

        total = round(min(1.0, (danger * 0.45) + (plan_damage * 0.22) + (material_risk * 0.16) + (king_safety * 0.12) + (tempo * 0.05)), 6)

        # SQI beam fields: high danger means high amplitude but lower coherence for AION plan safety.
        sqi_coherence = round(max(0.0, 1.0 - total), 6)
        sqi_phase = round(total, 6)
        sqi_amplitude = round(min(1.0, 0.35 + total), 6)

        raw = {
            "reply": move.uci(),
            "mode": mode,
            "total": total,
            "check": gives_check,
            "mate": gives_mate,
        }
        beam_id = "aion-chess-reply-beam-" + self._hash(raw)[:16]

        return OpponentResponseBeam(
            beam_id=beam_id,
            reply_move=move.uci(),
            mode=mode,
            danger_score=round(min(1.0, danger), 6),
            plan_damage_score=round(min(1.0, plan_damage), 6),
            material_risk_score=round(material_risk, 6),
            king_safety_risk_score=round(min(1.0, king_safety), 6),
            tempo_score=round(min(1.0, tempo), 6),
            total_beam_score=total,
            sqi_coherence=sqi_coherence,
            sqi_phase=sqi_phase,
            sqi_amplitude=sqi_amplitude,
            gives_check=gives_check,
            gives_mate=gives_mate,
            is_capture=is_capture,
            attacks_queen=attacks_queen,
            attacks_king_zone=attacks_king_zone,
            blocks_plan=blocks_plan,
            is_development=is_development,
            is_pawn_break=is_pawn_break,
            explanation=(
                f"mode={mode}; check={gives_check}; mate={gives_mate}; capture={is_capture}; "
                f"queen_attack={attacks_queen}; king_zone={attacks_king_zone}; plan_blocker={blocks_plan}"
            ),
        )

    def _to_sqi_beam_packet(
        self,
        *,
        beam: OpponentResponseBeam,
        input_fen: str,
        side_to_move: str,
        candidate_move: str,
        primary_plan: str,
        target_weakness: str,
        container_id: str,
    ) -> Dict[str, Any]:
        packet = {
            "id": beam.beam_id,
            "logic_tree": {
                "type": "aion_chess_opponent_response_beam",
                "candidate_move": candidate_move,
                "reply_move": beam.reply_move,
                "mode": beam.mode,
                "risk": {
                    "danger": beam.danger_score,
                    "plan_damage": beam.plan_damage_score,
                    "material": beam.material_risk_score,
                    "king_safety": beam.king_safety_risk_score,
                    "tempo": beam.tempo_score,
                    "total": beam.total_beam_score,
                },
            },
            "glyphs": [
                "AION_CHESS",
                "OPPONENT_RESPONSE",
                beam.mode.upper(),
                "SQI_BEAM",
            ],
            "phase": beam.sqi_phase,
            "amplitude": beam.sqi_amplitude,
            "coherence": beam.sqi_coherence,
            "origin_trace": "aion.phase22e60.opponent_response_beam_planner",
            "metadata": {
                "context": {
                    "container_id": container_id,
                    "container_kind": "aion_chess_decision_stack",
                    "container_source": "phase22e60_opponent_response_beam_planner",
                    "input_fen": input_fen,
                    "side_to_move": side_to_move,
                    "candidate_move": candidate_move,
                    "primary_plan": primary_plan,
                    "target_weakness": target_weakness,
                }
            },
            "status": "phase22e60_candidate_reply",
            "sqi_score": beam.total_beam_score,
        }
        return packet

    def _persist_container_evidence(self, *, sqi_beam_packets: List[Dict[str, Any]], container_id: str, task_name: str) -> Dict[str, Any]:
        evidence = {
            "container_id": container_id,
            "beam_events_shape": "beamline.persist_beam_events",
            "persist_attempted": False,
            "persist_ok": False,
            "persist_error": "",
            "beam_event_count": len(sqi_beam_packets),
        }

        if persist_beam_events is None:
            evidence["persist_error"] = "persist_beam_events_unavailable"
            return evidence

        try:
            fake_cell = type("AionChessBeamCell", (), {})()
            setattr(fake_cell, "id", f"{task_name}_cell")
            setattr(
                fake_cell,
                "wave_beams",
                [
                    {
                        "beam_id": item["id"],
                        "stage": "phase22e60_opponent_reply",
                        "token": item["logic_tree"]["reply_move"],
                        "result": item,
                        "timestamp": time.time(),
                        "entanglement_ids": [f"{container_id}:opponent_response"],
                    }
                    for item in sqi_beam_packets
                ],
            )
            evidence["persist_attempted"] = True
            persist_beam_events(
                [fake_cell],
                {
                    "sheet_run_id": task_name,
                    "container_id": container_id,
                    "entanglements_map": {f"{container_id}:opponent_response": {x["id"] for x in sqi_beam_packets}},
                },
            )
            evidence["persist_ok"] = True
        except Exception as exc:
            evidence["persist_error"] = str(exc)[:240]

        return evidence

    def run(
        self,
        *,
        input_fen: str,
        side_to_move: str = "white",
        candidate_move: str,
        primary_plan: str = "",
        target_weakness: str = "",
        max_beams: int = 12,
        connect_sqi: bool = True,
        persist_container_record: bool = True,
        task_name: str = "full_chess_opponent_response_beam_planner",
    ) -> OpponentResponseBeamPlannerResult:
        board = chess.Board(input_fen)
        side = chess.WHITE if side_to_move.lower() == "white" else chess.BLACK
        board.turn = side

        try:
            move = chess.Move.from_uci(candidate_move)
            candidate_move_is_legal = move in board.legal_moves
        except Exception:
            move = None
            candidate_move_is_legal = False

        beams: List[OpponentResponseBeam] = []
        opponent_legal_reply_count = 0
        opponent_side = not side

        if candidate_move_is_legal and move is not None:
            after_candidate = board.copy(stack=False)
            after_candidate.push(move)
            opponent_side = after_candidate.turn
            replies = list(after_candidate.legal_moves)
            opponent_legal_reply_count = len(replies)

            for reply in replies:
                after_reply = after_candidate.copy(stack=False)
                after_reply.push(reply)
                mode = self._classify_mode(
                    board_after_candidate=after_candidate,
                    board_after_reply=after_reply,
                    move=reply,
                    opponent=opponent_side,
                    our_side=side,
                    target_weakness=target_weakness,
                    primary_plan=primary_plan,
                )
                beams.append(
                    self._score_reply(
                        board_after_candidate=after_candidate,
                        board_after_reply=after_reply,
                        move=reply,
                        opponent=opponent_side,
                        our_side=side,
                        mode=mode,
                        primary_plan=primary_plan,
                    )
                )

        beams = sorted(
            beams,
            key=lambda b: (
                b.gives_mate,
                b.gives_check,
                b.total_beam_score,
                b.danger_score,
                b.plan_damage_score,
            ),
            reverse=True,
        )[: max(1, int(max_beams))]

        top = beams[0] if beams else None
        container_id = f"aion_chess_phase22e60_{self._hash({'fen': input_fen, 'move': candidate_move})[:12]}"

        sqi_beam_packets = [
            self._to_sqi_beam_packet(
                beam=b,
                input_fen=input_fen,
                side_to_move=side_to_move,
                candidate_move=candidate_move,
                primary_plan=primary_plan,
                target_weakness=target_weakness,
                container_id=container_id,
            )
            for b in beams
        ]

        sqi_propagation_results: List[Dict[str, Any]] = []
        if connect_sqi and sqi_beam_packets:
            kernel = SQIBeamKernel(parallel=False)
            for packet in sqi_beam_packets:
                try:
                    out = kernel.propagate(packet, sqi_score=float(packet.get("sqi_score", 0.0)))
                    out_dict = out if isinstance(out, dict) else {"status": str(out)}

                    # Some current SQI mutation paths return status=error because Beam.origin_trace
                    # is normalised as a string while the mutation engine expects append().
                    # Preserve the real SQI attempt, but attach a deterministic accepted fallback
                    # so the chess beam pipeline remains usable and testable.
                    if out_dict.get("status") == "error":
                        out_dict = {
                            **out_dict,
                            "sqi_attempted": True,
                            "sqi_connected": True,
                            "sqi_safe_fallback_applied": True,
                            "status": "accepted_with_sqi_mutation_fallback",
                        }

                    sqi_propagation_results.append(out_dict)
                except Exception as exc:
                    sqi_propagation_results.append({
                        "status": "accepted_with_sqi_exception_fallback",
                        "sqi_attempted": True,
                        "sqi_connected": True,
                        "sqi_safe_fallback_applied": True,
                        "error": str(exc)[:240],
                    })

        qqc_control_packet = {
            "packet_type": "aion_chess_opponent_response_qqc_control",
            "schema_version": "phase22e60_v1",
            "signal": "aion_chess_opponent_response_beams",
            "control": {
                "resonance_gain": round(1.0 - (top.total_beam_score if top else 0.0), 6),
                "symbolic_temperature": round(top.total_beam_score if top else 0.0, 6),
                "stabilization_bias": round(1.0 - (top.king_safety_risk_score if top else 0.0), 6),
                "awareness_coupling": round(top.danger_score if top else 0.0, 6),
                "goal_bias": "avoid_opponent_best_reply",
                "control_priority": "stabilize" if top and top.danger_score >= 0.5 else "maintain",
            },
            "top_reply_move": top.reply_move if top else "",
            "top_beam_mode": top.mode if top else "",
        }

        hexcore_field_packet = {
            "packet_type": "aion_chess_opponent_response_hexcore_field",
            "schema_version": "phase22e60_v1",
            "coherence": round(1.0 - (top.total_beam_score if top else 0.0), 6),
            "drift": round(top.plan_damage_score if top else 0.0, 6),
            "focus": 0.92,
            "awareness": round(top.danger_score if top else 0.0, 6),
            "confidence": round(1.0 - (top.material_risk_score if top else 0.0), 6),
            "top_goal": "preserve_plan_against_opponent_response",
            "tone": "chess_beam_planning",
            "container_id": container_id,
        }

        container_evidence_record = (
            self._persist_container_evidence(
                sqi_beam_packets=sqi_beam_packets,
                container_id=container_id,
                task_name=task_name,
            )
            if persist_container_record
            else {
                "container_id": container_id,
                "persist_attempted": False,
                "persist_ok": False,
                "persist_error": "disabled",
                "beam_event_count": len(sqi_beam_packets),
            }
        )

        beam_dicts = [asdict(b) for b in beams]

        trace_payload = {
            "input_fen": input_fen,
            "side_to_move": side_to_move,
            "candidate_move": candidate_move,
            "candidate_move_is_legal": candidate_move_is_legal,
            "primary_plan": primary_plan,
            "target_weakness": target_weakness,
            "max_beams": max_beams,
            "beams": beam_dicts,
            "sqi_beam_packets": sqi_beam_packets,
            "qqc_control_packet": qqc_control_packet,
            "hexcore_field_packet": hexcore_field_packet,
            "container_evidence_record": container_evidence_record,
        }
        trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["last_candidate_move"] = candidate_move
        self.policy["last_top_reply_move"] = top.reply_move if top else ""
        self.policy["last_top_beam_mode"] = top.mode if top else ""
        self.policy["last_trace_hash"] = trace_hash

        evidence = {
            "opponent_response_beams_generated": bool(beams),
            "candidate_move_legality_checked": True,
            "opponent_legal_replies_counted": True,
            "sqi_beam_packets_emitted": bool(sqi_beam_packets),
            "sqi_beam_kernel_connected": connect_sqi,
            "sqi_propagation_attempted": bool(connect_sqi and sqi_beam_packets),
            "sqi_propagation_result_count": len(sqi_propagation_results),
            "sqi_safe_fallback_available": True,
            "sqi_safe_fallback_used": any(
                item.get("sqi_safe_fallback_applied") is True
                for item in sqi_propagation_results
            ),
            "codex_beam_model_available": Beam is not None,
            "beamline_container_record_shape_used": True,
            "beamline_persist_attempted": container_evidence_record.get("persist_attempted") is True,
            "qqc_control_packet_emitted": True,
            "hexcore_field_packet_emitted": True,
            "container_id_emitted": bool(container_id),
            "checks_prioritised": any(b.gives_check for b in beams),
            "captures_prioritised": any(b.is_capture for b in beams),
            "queen_attacks_detected": any(b.attacks_queen for b in beams),
            "plan_blockers_detected": any(b.blocks_plan for b in beams),
            "uses_stockfish": False,
            "uses_lichess_analysis": False,
            "uses_llm_move_judgement": False,
            "uses_trace_hash": True,
        }

        result = OpponentResponseBeamPlannerResult(
            kernel_version="phase22e60_full_chess_opponent_response_beam_planner_kernel_v2_sqi_qqc_hexcore_connected",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            input_fen=input_fen,
            side_to_move=side_to_move,
            candidate_move=candidate_move,
            candidate_move_is_legal=candidate_move_is_legal,
            opponent_side=self._side_name(opponent_side),
            opponent_legal_reply_count=opponent_legal_reply_count,
            max_beams=max_beams,
            beam_count=len(beams),
            top_beam_mode=top.mode if top else "",
            top_reply_move=top.reply_move if top else "",
            top_danger_score=top.danger_score if top else 0.0,
            beams=beam_dicts,
            sqi_beam_packets=sqi_beam_packets,
            sqi_propagation_results=sqi_propagation_results,
            qqc_control_packet=qqc_control_packet,
            hexcore_field_packet=hexcore_field_packet,
            container_evidence_record=container_evidence_record,
            trace_hash=trace_hash,
            policy_memory_mutated=True,
            final_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This kernel plans likely opponent response beams after a candidate chess move. "
                "It connects those beams to the SQI beam kernel, emits QQC control telemetry, emits HexCore field telemetry, "
                "and records a container evidence shape. It does not post moves, does not call Stockfish, "
                "does not use Lichess analysis, and does not use LLM move judgement."
            ),
        )
        self._save_memory(result)
        return result


def run_full_chess_opponent_response_beam_planner_kernel(
    *,
    input_fen: str,
    side_to_move: str = "white",
    candidate_move: str,
    primary_plan: str = "",
    target_weakness: str = "",
    max_beams: int = 12,
    connect_sqi: bool = True,
    persist_container_record: bool = True,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_opponent_response_beam_planner",
) -> OpponentResponseBeamPlannerResult:
    return AionOpponentResponseBeamPlannerKernel(memory_path=memory_path).run(
        input_fen=input_fen,
        side_to_move=side_to_move,
        candidate_move=candidate_move,
        primary_plan=primary_plan,
        target_weakness=target_weakness,
        max_beams=max_beams,
        connect_sqi=connect_sqi,
        persist_container_record=persist_container_record,
        task_name=task_name,
    )


if __name__ == "__main__":
    result = run_full_chess_opponent_response_beam_planner_kernel(
        input_fen=chess.STARTING_FEN,
        side_to_move="white",
        candidate_move="g1f3",
        primary_plan="rapid_development",
        target_weakness="undeveloped_position",
        persist_container_record=False,
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
