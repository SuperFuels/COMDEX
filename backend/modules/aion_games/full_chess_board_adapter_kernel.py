"""AION Phase 22B.7 — Full 8x8 Chess Board Adapter Kernel.

This phase moves from controlled mini-chess to full-board chess grounding.

It proves:
- 8x8 board representation;
- standard initial chess position;
- piece ownership;
- legal opening pawn moves;
- legal opening knight moves;
- blocked bishop/rook/queen/king moves rejected;
- deterministic trace hash;
- no LLM shortcut.

This is not full chess mastery yet.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_FULL_CHESS_MEMORY_PATH = Path("data/aion_games/full_chess_board_adapter_memory.json")

Position = Tuple[int, int]


@dataclass(frozen=True)
class FullChessPiece:
    piece_id: str
    owner: str
    kind: str
    position: Position
    value: int

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["position"] = list(self.position)
        return data


@dataclass(frozen=True)
class FullChessMove:
    move_id: str
    piece_id: str
    from_position: Position
    to_position: Position
    legal: bool
    move_type: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["from_position"] = list(self.from_position)
        data["to_position"] = list(self.to_position)
        return data


@dataclass(frozen=True)
class FullChessBoardAdapterResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    board_size: int
    initial_piece_count: int
    white_piece_count: int
    black_piece_count: int
    board_coordinates_valid: bool
    standard_start_position: bool
    generated_legal_opening_moves: List[Dict[str, Any]]
    rejected_illegal_opening_moves: List[Dict[str, Any]]
    legal_opening_move_count: int
    illegal_opening_move_count: int
    pawn_opening_move_count: int
    knight_opening_move_count: int
    blocked_piece_rejection_count: int
    selected_opening_move: Dict[str, Any]
    selected_move_legal: bool
    full_chess_trace_hash: str
    final_full_chess_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionFullChessBoardAdapterKernel:
    def __init__(self, *, memory_path: Optional[Path] = None):
        self.memory_path = Path(memory_path or DEFAULT_FULL_CHESS_MEMORY_PATH)
        self.memory_loaded = False
        self.board_size = 8

        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "full_board_grounding_count": 0,
            "legal_opening_move_count": 0,
            "illegal_opening_rejection_count": 0,
            "last_selected_opening_move": None,
            "last_full_chess_trace_hash": None,
        }

        self._load_memory()
        self.pieces = self._initial_position()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return
        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if isinstance(data, dict):
            policy = data.get("full_chess_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True

    def _save_memory(self, result: FullChessBoardAdapterResult) -> None:
        previous = {}
        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase22b7_full_chess_board_adapter_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "full_chess_policy": result.final_full_chess_policy,
            "last_selected_opening_move": result.selected_opening_move,
            "last_full_chess_trace_hash": result.full_chess_trace_hash,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
            "boundary_statement": result.boundary_statement,
        }
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _hash(self, payload: Dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _initial_position(self) -> List[FullChessPiece]:
        values = {
            "king": 100,
            "queen": 9,
            "rook": 5,
            "bishop": 3,
            "knight": 3,
            "pawn": 1,
        }

        back_rank = ["rook", "knight", "bishop", "queen", "king", "bishop", "knight", "rook"]
        pieces: List[FullChessPiece] = []

        for x, kind in enumerate(back_rank):
            pieces.append(FullChessPiece(f"W_{kind.upper()}_{x}", "white", kind, (x, 0), values[kind]))
            pieces.append(FullChessPiece(f"B_{kind.upper()}_{x}", "black", kind, (x, 7), values[kind]))

        for x in range(8):
            pieces.append(FullChessPiece(f"W_PAWN_{x}", "white", "pawn", (x, 1), values["pawn"]))
            pieces.append(FullChessPiece(f"B_PAWN_{x}", "black", "pawn", (x, 6), values["pawn"]))

        return pieces

    def _inside(self, pos: Position) -> bool:
        x, y = pos
        return 0 <= x < self.board_size and 0 <= y < self.board_size

    def _piece_at(self, pos: Position) -> Optional[FullChessPiece]:
        for piece in self.pieces:
            if piece.position == pos:
                return piece
        return None

    def _is_clear_between(self, start: Position, end: Position) -> bool:
        sx, sy = start
        ex, ey = end

        dx = 0 if ex == sx else (1 if ex > sx else -1)
        dy = 0 if ey == sy else (1 if ey > sy else -1)

        cur = (sx + dx, sy + dy)
        while cur != end:
            if self._piece_at(cur) is not None:
                return False
            cur = (cur[0] + dx, cur[1] + dy)

        return True

    def _legal_pawn_move(self, piece: FullChessPiece, target: Position) -> tuple[bool, str]:
        sx, sy = piece.position
        tx, ty = target
        direction = 1 if piece.owner == "white" else -1
        start_rank = 1 if piece.owner == "white" else 6

        if tx == sx and ty == sy + direction and self._piece_at(target) is None:
            return True, "legal pawn one-step opening move"

        if tx == sx and sy == start_rank and ty == sy + (2 * direction):
            middle = (sx, sy + direction)
            if self._piece_at(middle) is None and self._piece_at(target) is None:
                return True, "legal pawn two-step opening move"

        return False, "illegal pawn move"

    def _legal_knight_move(self, piece: FullChessPiece, target: Position) -> tuple[bool, str]:
        sx, sy = piece.position
        tx, ty = target
        dx = abs(tx - sx)
        dy = abs(ty - sy)

        occupant = self._piece_at(target)
        if occupant is not None and occupant.owner == piece.owner:
            return False, "target occupied by own piece"

        if sorted([dx, dy]) == [1, 2]:
            return True, "legal knight opening move"

        return False, "illegal knight geometry"

    def _legal_sliding_move(self, piece: FullChessPiece, target: Position) -> tuple[bool, str]:
        sx, sy = piece.position
        tx, ty = target
        dx = tx - sx
        dy = ty - sy

        if piece.kind == "rook" and not (dx == 0 or dy == 0):
            return False, "illegal rook geometry"

        if piece.kind == "bishop" and abs(dx) != abs(dy):
            return False, "illegal bishop geometry"

        if piece.kind == "queen" and not (dx == 0 or dy == 0 or abs(dx) == abs(dy)):
            return False, "illegal queen geometry"

        if not self._is_clear_between(piece.position, target):
            return False, "path blocked by starting position"

        occupant = self._piece_at(target)
        if occupant is not None and occupant.owner == piece.owner:
            return False, "target occupied by own piece"

        return True, f"legal {piece.kind} move"

    def _legal_king_move(self, piece: FullChessPiece, target: Position) -> tuple[bool, str]:
        sx, sy = piece.position
        tx, ty = target
        if max(abs(tx - sx), abs(ty - sy)) != 1:
            return False, "illegal king geometry or unsupported castle"
        occupant = self._piece_at(target)
        if occupant is not None and occupant.owner == piece.owner:
            return False, "target occupied by own piece"
        return True, "legal king one-step move"

    def _evaluate_move(self, move_id: str, piece: FullChessPiece, target: Position) -> FullChessMove:
        if not self._inside(target):
            return FullChessMove(move_id, piece.piece_id, piece.position, target, False, "invalid", "outside board")

        if piece.kind == "pawn":
            legal, reason = self._legal_pawn_move(piece, target)
        elif piece.kind == "knight":
            legal, reason = self._legal_knight_move(piece, target)
        elif piece.kind in {"rook", "bishop", "queen"}:
            legal, reason = self._legal_sliding_move(piece, target)
        elif piece.kind == "king":
            legal, reason = self._legal_king_move(piece, target)
        else:
            legal, reason = False, "unknown piece"

        occupant = self._piece_at(target)
        move_type = "capture" if legal and occupant is not None and occupant.owner != piece.owner else "quiet"
        if not legal:
            move_type = "illegal"

        return FullChessMove(move_id, piece.piece_id, piece.position, target, legal, move_type, reason)

    def _generate_opening_moves(self) -> tuple[List[FullChessMove], List[FullChessMove]]:
        legal: List[FullChessMove] = []
        illegal: List[FullChessMove] = []

        move_index = 1

        # Full standard chess opening legal moves: 16 pawn moves + 4 knight moves.
        for piece in self.pieces:
            if piece.owner != "white":
                continue

            targets: List[Position] = []

            if piece.kind == "pawn":
                x, y = piece.position
                targets.extend([(x, y + 1), (x, y + 2)])

            if piece.kind == "knight":
                x, y = piece.position
                targets.extend([
                    (x - 2, y + 1),
                    (x - 1, y + 2),
                    (x + 1, y + 2),
                    (x + 2, y + 1),
                ])

            for target in targets:
                move = self._evaluate_move(f"OPEN-{move_index}", piece, target)
                move_index += 1
                if move.legal:
                    legal.append(move)
                else:
                    illegal.append(move)

        # Explicit blocked opening attempts.
        blocked_attempts = [
            ("BLOCK-BISHOP", "W_BISHOP_2", (4, 2)),
            ("BLOCK-ROOK", "W_ROOK_0", (0, 3)),
            ("BLOCK-QUEEN", "W_QUEEN_3", (3, 3)),
            ("BLOCK-KING", "W_KING_4", (4, 1)),
        ]

        piece_by_id = {p.piece_id: p for p in self.pieces}
        for move_id, piece_id, target in blocked_attempts:
            move = self._evaluate_move(move_id, piece_by_id[piece_id], target)
            if move.legal:
                legal.append(move)
            else:
                illegal.append(move)

        return legal, illegal

    def run(self, *, task_name: str = "full_chess_board_adapter") -> FullChessBoardAdapterResult:
        legal_moves, illegal_moves = self._generate_opening_moves()

        pawn_opening_move_count = sum(1 for m in legal_moves if "PAWN" in m.piece_id)
        knight_opening_move_count = sum(1 for m in legal_moves if "KNIGHT" in m.piece_id)
        blocked_piece_rejection_count = sum(1 for m in illegal_moves if m.move_id.startswith("BLOCK"))

        selected = next(m for m in legal_moves if m.piece_id == "W_PAWN_4" and m.to_position == (4, 3))

        board_coordinates_valid = all(self._inside(p.position) for p in self.pieces)
        white_piece_count = sum(1 for p in self.pieces if p.owner == "white")
        black_piece_count = sum(1 for p in self.pieces if p.owner == "black")
        standard_start_position = (
            len(self.pieces) == 32
            and white_piece_count == 16
            and black_piece_count == 16
            and self._piece_at((4, 0)).kind == "king"
            and self._piece_at((4, 7)).kind == "king"
        )

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        if board_coordinates_valid and standard_start_position:
            self.policy["full_board_grounding_count"] = int(self.policy.get("full_board_grounding_count", 0)) + 1
        self.policy["legal_opening_move_count"] = int(self.policy.get("legal_opening_move_count", 0)) + len(legal_moves)
        self.policy["illegal_opening_rejection_count"] = int(self.policy.get("illegal_opening_rejection_count", 0)) + len(illegal_moves)
        self.policy["last_selected_opening_move"] = selected.to_dict()

        trace_payload = {
            "board_size": self.board_size,
            "pieces": [p.to_dict() for p in self.pieces],
            "legal_moves": [m.to_dict() for m in legal_moves],
            "illegal_moves": [m.to_dict() for m in illegal_moves],
            "selected_opening_move": selected.to_dict(),
            "uses_llm_shortcut": False,
        }
        trace_hash = self._hash(trace_payload)
        self.policy["last_full_chess_trace_hash"] = trace_hash

        evidence = {
            "uses_llm_shortcut": False,
            "uses_8x8_board": True,
            "uses_standard_start_position": standard_start_position,
            "uses_piece_ownership": True,
            "uses_legal_pawn_opening_moves": pawn_opening_move_count == 16,
            "uses_legal_knight_opening_moves": knight_opening_move_count == 4,
            "rejects_blocked_sliding_pieces": blocked_piece_rejection_count >= 4,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = FullChessBoardAdapterResult(
            kernel_version="phase22b7_full_chess_board_adapter_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            board_size=self.board_size,
            initial_piece_count=len(self.pieces),
            white_piece_count=white_piece_count,
            black_piece_count=black_piece_count,
            board_coordinates_valid=board_coordinates_valid,
            standard_start_position=standard_start_position,
            generated_legal_opening_moves=[m.to_dict() for m in legal_moves],
            rejected_illegal_opening_moves=[m.to_dict() for m in illegal_moves],
            legal_opening_move_count=len(legal_moves),
            illegal_opening_move_count=len(illegal_moves),
            pawn_opening_move_count=pawn_opening_move_count,
            knight_opening_move_count=knight_opening_move_count,
            blocked_piece_rejection_count=blocked_piece_rejection_count,
            selected_opening_move=selected.to_dict(),
            selected_move_legal=selected.legal,
            full_chess_trace_hash=trace_hash,
            final_full_chess_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This demonstrates full 8x8 chess board grounding and opening move legality. "
                "It does not yet implement full chess mastery, castling, en passant, promotion, full checkmate search, "
                "general intelligence, or biological consciousness."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_board_adapter_kernel(
    *,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_board_adapter",
) -> FullChessBoardAdapterResult:
    return AionFullChessBoardAdapterKernel(memory_path=memory_path).run(task_name=task_name)


if __name__ == "__main__":
    result = run_full_chess_board_adapter_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\\n✅ Full chess board adapter memory saved to: {result.memory_path}")
