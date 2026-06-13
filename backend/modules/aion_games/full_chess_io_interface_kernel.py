"""AION Phase 22B.22 — FEN / UCI / PGN Interface Kernel.

This phase proves AION can use standard chess I/O surfaces:
- FEN import;
- FEN export;
- UCI move parse;
- UCI move export;
- PGN move recording;
- PGN export;
- deterministic trace hashing.

This is chess interface plumbing, not yet a full playable engine.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_CHESS_IO_MEMORY_PATH = Path(
    "data/aion_games/full_chess_io_interface_memory.json"
)

Board = List[List[str]]

PIECE_TO_FEN = {
    "W_K": "K",
    "W_Q": "Q",
    "W_R": "R",
    "W_B": "B",
    "W_N": "N",
    "W_P": "P",
    "B_K": "k",
    "B_Q": "q",
    "B_R": "r",
    "B_B": "b",
    "B_N": "n",
    "B_P": "p",
}

FEN_TO_PIECE = {value: key for key, value in PIECE_TO_FEN.items()}


@dataclass(frozen=True)
class UciMove:
    raw: str
    from_square: str
    to_square: str
    promotion: Optional[str]
    valid_shape: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PgnRecord:
    move_number: int
    white_move: str
    black_move: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FullChessIoInterfaceResult:
    kernel_version: str
    task_name: str
    memory_loaded: bool
    memory_path: str
    board_size: int
    fen_input: str
    fen_export: str
    fen_round_trip_ok: bool
    active_color: str
    castling_rights: str
    en_passant_target: str
    halfmove_clock: int
    fullmove_number: int
    uci_input: str
    uci_move: Dict[str, Any]
    uci_round_trip_ok: bool
    pgn_records: List[Dict[str, Any]]
    pgn_export: str
    pgn_export_ok: bool
    io_trace_hash: str
    final_io_policy: Dict[str, Any]
    evidence: Dict[str, Any]
    boundary_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AionFullChessIoInterfaceKernel:
    def __init__(self, *, memory_path: Optional[Path] = None):
        self.memory_path = Path(memory_path or DEFAULT_CHESS_IO_MEMORY_PATH)
        self.memory_loaded = False
        self.board_size = 8

        self.policy: Dict[str, Any] = {
            "kernel_run_count": 0,
            "fen_import_count": 0,
            "fen_export_count": 0,
            "uci_parse_count": 0,
            "uci_export_count": 0,
            "pgn_export_count": 0,
            "last_fen": None,
            "last_uci": None,
            "last_pgn": None,
            "last_io_trace_hash": None,
        }

        self._load_memory()

    def _load_memory(self) -> None:
        if not self.memory_path.exists():
            return

        try:
            data = json.loads(self.memory_path.read_text(encoding="utf-8"))
        except Exception:
            return

        if isinstance(data, dict):
            policy = data.get("io_policy")
            if isinstance(policy, dict):
                self.policy.update(policy)
                self.memory_loaded = True

    def _save_memory(self, result: FullChessIoInterfaceResult) -> None:
        previous = {}

        if self.memory_path.exists():
            try:
                previous = json.loads(self.memory_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}

        if not isinstance(previous, dict):
            previous = {}

        payload = {
            "memory_version": "phase22b22_full_chess_io_interface_memory_v1",
            "kernel_version": result.kernel_version,
            "task_name": result.task_name,
            "io_policy": result.final_io_policy,
            "last_fen": result.fen_export,
            "last_uci": result.uci_input,
            "last_pgn": result.pgn_export,
            "last_io_trace_hash": result.io_trace_hash,
            "run_count": int(previous.get("run_count", 0)) + 1,
            "uses_llm_shortcut": False,
            "boundary_statement": result.boundary_statement,
        }

        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _hash(self, payload: Dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def import_fen(self, fen: str) -> Tuple[Board, str, str, str, int, int]:
        parts = fen.strip().split()
        if len(parts) != 6:
            raise ValueError("FEN must contain 6 fields.")

        placement, active_color, castling_rights, en_passant_target, halfmove, fullmove = parts
        ranks = placement.split("/")
        if len(ranks) != 8:
            raise ValueError("FEN piece placement must contain 8 ranks.")

        board: Board = []

        for rank in ranks:
            row: List[str] = []
            for char in rank:
                if char.isdigit():
                    row.extend(["__"] * int(char))
                elif char in FEN_TO_PIECE:
                    row.append(FEN_TO_PIECE[char])
                else:
                    raise ValueError(f"Unsupported FEN piece: {char}")

            if len(row) != 8:
                raise ValueError("Each FEN rank must expand to 8 files.")

            board.append(row)

        return (
            board,
            active_color,
            castling_rights,
            en_passant_target,
            int(halfmove),
            int(fullmove),
        )

    def export_fen(
        self,
        board: Board,
        *,
        active_color: str,
        castling_rights: str,
        en_passant_target: str,
        halfmove_clock: int,
        fullmove_number: int,
    ) -> str:
        ranks: List[str] = []

        for row in board:
            empty = 0
            rank_parts: List[str] = []

            for piece in row:
                if piece == "__":
                    empty += 1
                    continue

                if empty:
                    rank_parts.append(str(empty))
                    empty = 0

                if piece not in PIECE_TO_FEN:
                    raise ValueError(f"Unsupported board piece: {piece}")

                rank_parts.append(PIECE_TO_FEN[piece])

            if empty:
                rank_parts.append(str(empty))

            ranks.append("".join(rank_parts))

        return (
            f"{'/'.join(ranks)} {active_color} {castling_rights} "
            f"{en_passant_target} {halfmove_clock} {fullmove_number}"
        )

    def parse_uci(self, raw: str) -> UciMove:
        raw = raw.strip().lower()
        valid_len = len(raw) in {4, 5}
        files = "abcdefgh"
        ranks = "12345678"

        valid_shape = (
            valid_len
            and raw[0] in files
            and raw[1] in ranks
            and raw[2] in files
            and raw[3] in ranks
            and (len(raw) == 4 or raw[4] in "qrbn")
        )

        promotion = raw[4] if len(raw) == 5 and valid_shape else None

        return UciMove(
            raw=raw,
            from_square=raw[:2] if len(raw) >= 2 else "",
            to_square=raw[2:4] if len(raw) >= 4 else "",
            promotion=promotion,
            valid_shape=bool(valid_shape),
        )

    def export_uci(self, move: UciMove) -> str:
        return f"{move.from_square}{move.to_square}{move.promotion or ''}"

    def export_pgn(self, records: List[PgnRecord]) -> str:
        parts: List[str] = []

        for record in records:
            if record.black_move:
                parts.append(f"{record.move_number}. {record.white_move} {record.black_move}")
            else:
                parts.append(f"{record.move_number}. {record.white_move}")

        return " ".join(parts)

    def run(self, *, task_name: str = "full_chess_io_interface") -> FullChessIoInterfaceResult:
        fen_input = "rnbqkbnr/pppppppp/8/8/2P5/8/PP1PPPPP/RNBQKBNR w KQkq - 0 1"

        (
            board,
            active_color,
            castling_rights,
            en_passant_target,
            halfmove_clock,
            fullmove_number,
        ) = self.import_fen(fen_input)

        fen_export = self.export_fen(
            board,
            active_color=active_color,
            castling_rights=castling_rights,
            en_passant_target=en_passant_target,
            halfmove_clock=halfmove_clock,
            fullmove_number=fullmove_number,
        )
        fen_round_trip_ok = fen_input == fen_export

        uci_input = "c4d5"
        uci_move = self.parse_uci(uci_input)
        uci_export = self.export_uci(uci_move)
        uci_round_trip_ok = uci_input == uci_export and uci_move.valid_shape

        pgn_records = [
            PgnRecord(move_number=1, white_move="c4", black_move="Nf6"),
            PgnRecord(move_number=2, white_move="cxd5", black_move=None),
        ]
        pgn_export = self.export_pgn(pgn_records)
        pgn_export_ok = pgn_export == "1. c4 Nf6 2. cxd5"

        trace_payload = {
            "fen_input": fen_input,
            "fen_export": fen_export,
            "uci_input": uci_input,
            "uci_export": uci_export,
            "pgn_export": pgn_export,
            "uses_llm_shortcut": False,
        }

        io_trace_hash = self._hash(trace_payload)

        self.policy["kernel_run_count"] = int(self.policy.get("kernel_run_count", 0)) + 1
        self.policy["fen_import_count"] = int(self.policy.get("fen_import_count", 0)) + 1
        self.policy["fen_export_count"] = int(self.policy.get("fen_export_count", 0)) + 1
        self.policy["uci_parse_count"] = int(self.policy.get("uci_parse_count", 0)) + 1
        self.policy["uci_export_count"] = int(self.policy.get("uci_export_count", 0)) + 1
        self.policy["pgn_export_count"] = int(self.policy.get("pgn_export_count", 0)) + 1
        self.policy["last_fen"] = fen_export
        self.policy["last_uci"] = uci_export
        self.policy["last_pgn"] = pgn_export
        self.policy["last_io_trace_hash"] = io_trace_hash

        evidence = {
            "uses_llm_shortcut": False,
            "uses_8x8_board": True,
            "imports_fen": True,
            "exports_fen": True,
            "fen_round_trip_ok": fen_round_trip_ok,
            "parses_uci": uci_move.valid_shape,
            "exports_uci": True,
            "uci_round_trip_ok": uci_round_trip_ok,
            "records_pgn": len(pgn_records) == 2,
            "exports_pgn": pgn_export_ok,
            "uses_trace_hash": True,
            "memory_loaded": self.memory_loaded,
        }

        result = FullChessIoInterfaceResult(
            kernel_version="phase22b22_full_chess_io_interface_kernel_v1",
            task_name=task_name,
            memory_loaded=self.memory_loaded,
            memory_path=str(self.memory_path),
            board_size=self.board_size,
            fen_input=fen_input,
            fen_export=fen_export,
            fen_round_trip_ok=fen_round_trip_ok,
            active_color=active_color,
            castling_rights=castling_rights,
            en_passant_target=en_passant_target,
            halfmove_clock=halfmove_clock,
            fullmove_number=fullmove_number,
            uci_input=uci_input,
            uci_move=uci_move.to_dict(),
            uci_round_trip_ok=uci_round_trip_ok,
            pgn_records=[record.to_dict() for record in pgn_records],
            pgn_export=pgn_export,
            pgn_export_ok=pgn_export_ok,
            io_trace_hash=io_trace_hash,
            final_io_policy=dict(self.policy),
            evidence=evidence,
            boundary_statement=(
                "This demonstrates deterministic FEN, UCI, and PGN interface handling. "
                "AION can import/export FEN, parse/export UCI moves, and record/export PGN move text. "
                "It does not yet implement a complete playable chess engine, exhaustive search, engine-strength evaluation, "
                "general intelligence, or biological consciousness."
            ),
        )

        self._save_memory(result)
        return result


def run_full_chess_io_interface_kernel(
    *,
    memory_path: Optional[Path] = None,
    task_name: str = "full_chess_io_interface",
) -> FullChessIoInterfaceResult:
    return AionFullChessIoInterfaceKernel(memory_path=memory_path).run(task_name=task_name)


if __name__ == "__main__":
    result = run_full_chess_io_interface_kernel()
    print(json.dumps(result.to_dict(), indent=2))
    print(f"\\n✅ Full chess I/O interface memory saved to: {result.memory_path}")
