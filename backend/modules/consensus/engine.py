# backend/modules/consensus/engine.py
from __future__ import annotations
import hashlib
import hmac
import json
import asyncio
import base64
import os
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Deque
import random
from backend.modules.consensus.sync_policy import SyncPolicy
from backend.modules.p2p.peer_store import load_peers_from_env, list_peers
from .store import load_state, save_state
from .types import Proposal, QC, Vote, VoteType
from .validator_set import ValidatorSet
from .finality_certificate import (
    build_finality_certificate,
    verify_finality_certificate,
    verify_finality_vote,
    vote_sign_bytes,
)
from .finality_checkpoint import load_trusted_checkpoint_from_env
from .ledger_commitment import empty_ledger_block, normalize_ledger_block
from .partition_recovery import (
    PHASE_BLOCK_CATCHUP,
    PHASE_HEALTHY,
    PHASE_PARTITION_SUSPECTED,
    PHASE_REJOIN_ASSESSING,
    PHASE_SAFETY_HALT,
    PHASE_SNAPSHOT_REQUIRED,
    PartitionRecoveryError,
    PartitionRecoveryStore,
    classify_validated_views,
    peer_digest,
)
from .protocol_upgrade import ProtocolUpgradeError, ProtocolUpgradeStore
from .validator_governance import sign_approval as sign_validator_governance_approval
from collections import deque
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Optional networking layer (PR2). If missing, engine still runs but won't broadcast.
_NET_OK = True
_NET_ERR = ""
try:
    from .net import (
        broadcast_proposal,
        broadcast_vote,
        ensure_peer_hello,
        request_sync_one,
        request_block,
        request_blocks,
    ) # type: ignore
except Exception as e:  # pragma: no cover
    _NET_OK = False
    _NET_ERR = str(e)
    broadcast_proposal = None  # type: ignore
    broadcast_vote = None  # type: ignore
    ensure_peer_hello = None  # type: ignore
    request_sync_one = None  # type: ignore
    request_block = None  # type: ignore
    request_blocks = None  # type: ignore

def _truthy(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _bounded_int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)) or default)
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))

def _stable_json_bytes(x: Any) -> bytes:
    try:
        return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except Exception:
        return repr(x).encode("utf-8")

def _best_prevoted_block_id(self, *, height: int, round: int) -> Optional[str]:
    h = int(height); r = int(round)
    best_bid: Optional[str] = None
    best_power = -1

    with self._lock:
        for (hh, rr, vt, bid), voters in self._votes.items():
            if int(hh) != h or int(rr) != r or str(vt) != "PREVOTE":
                continue
            power = 0
            for v in (voters or set()):
                power += self.vset.power_of(v)
            if power > best_power:
                best_power = power
                best_bid = str(bid)

    # defense-in-depth: ensure canonical block_id for (h,r)
    if best_bid:
        exp_leader = self.leader_for(h, r)
        if exp_leader:
            parsed = _parse_canon_block_id(best_bid)
            if parsed != (h, r, str(exp_leader)):
                return None

    return best_bid

def _proposal_fingerprint(p: Any) -> str:
    """
    Fingerprint proposal identity for determinism.
    Intentionally excludes ts_ms, sig_hex, and block contents (block_id is the identity).
    """
    try:
        if hasattr(p, "model_dump"):
            d = p.model_dump()
        else:
            d = dict(p)  # type: ignore[arg-type]
    except Exception:
        d = {
            "height": getattr(p, "height", None),
            "round": getattr(p, "round", None),
            "proposer": getattr(p, "proposer", None),
            "block_id": getattr(p, "block_id", None),
        }

    canon = {
        "height": int(d.get("height") or 0),
        "round": int(d.get("round") or 0),
        "proposer": str(d.get("proposer") or ""),
        "block_id": str(d.get("block_id") or ""),
        "ledger_commitment": str(d.get("ledger_commitment") or ""),
        "txs_root": str(d.get("txs_root") or ""),
    }
    return hashlib.sha256(_stable_json_bytes(canon)).hexdigest()

def _now_ms() -> float:
    return float(time.time() * 1000.0)

def _as_int(x: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        return int(x)
    except Exception:
        return default

def _canon_block_id(
    height: int,
    round: int,
    proposer: str,
    ledger_commitment: str | None = None,
) -> str:
    # MUST match tick() proposal creation format
    base = f"h{int(height)}-r{int(round)}-P{str(proposer)}"
    commitment = str(ledger_commitment or "").strip().lower()
    return f"{base}-C{commitment}" if commitment else base

def _is_qc_strictly_newer(a: QC, b: QC) -> bool:
    """
    PR6.1: monotonic QC ordering (height, then round).
    """
    ah = _as_int(getattr(a, "height", None), None)
    ar = _as_int(getattr(a, "round", None), None)
    bh = _as_int(getattr(b, "height", None), None)
    br = _as_int(getattr(b, "round", None), None)
    if ah is None or ar is None or bh is None or br is None:
        return False
    if ah != bh:
        return ah > bh
    return ar > br

def _parse_canon_block_id(bid: str) -> Optional[tuple[int, int, str]]:
    """
    Parse canonical block_id: "h{height}-r{round}-P{proposer}"
    Returns (height, round, proposer) or None.
    """
    s = str(bid or "").strip()
    if not s.startswith("h"):
        return None
    try:
        # split: h{h}-r{r}-P{proposer}
        parts = s.split("-")
        if len(parts) < 3:
            return None
        h_part = parts[0]  # "h12"
        r_part = parts[1]  # "r0"
        p_part = "-".join(parts[2:])  # "Pval1" (proposer may contain dashes)

        if not h_part.startswith("h") or not r_part.startswith("r") or not p_part.startswith("P"):
            return None

        h = int(h_part[1:])
        r = int(r_part[1:])
        proposer = p_part[1:]
        if "-C" in proposer:
            proposer, commitment = proposer.rsplit("-C", 1)
            if len(commitment) != 64:
                return None
            bytes.fromhex(commitment)
        if h <= 0 or r < 0 or not proposer:
            return None
        return (h, r, proposer)
    except Exception:
        return None


def _validate_qc_structural_or_error(
    qc: QC,
    *,
    vset: ValidatorSet,
    last_qc: Optional[QC] = None,
    expect_height: Optional[int] = None,
) -> Optional[str]:
    """
    Returns error string if invalid, else None.

    Enforces:
      - vote_type == PRECOMMIT
      - height/round sane
      - block_id canonical shape and matches qc.height/qc.round
      - voters in validator set + quorum power
      - monotonicity / no conflict vs last_qc (height,round); same (h,r) must not change block_id
      - optional expect_height check
    """
    try:
        h = int(getattr(qc, "height", 0) or 0)
        r = int(getattr(qc, "round", 0) or 0)
        vt = str(getattr(qc, "vote_type", "") or "").strip().upper()
        bid = str(getattr(qc, "block_id", "") or "").strip()
        voters = list(getattr(qc, "voters", None) or [])
    except Exception:
        return "qc decode failed"

    if vt != "PRECOMMIT":
        return "qc vote_type not PRECOMMIT"
    if h <= 0:
        return "qc height must be > 0"
    if r < 0:
        return "qc round must be >= 0"
    if expect_height is not None and int(expect_height) != int(h):
        return "qc height mismatch"
    if not bid:
        return "qc block_id required"

    parsed = _parse_canon_block_id(bid)
    if parsed is None:
        return "qc block_id not canonical"
    ph, pr, _pp = parsed
    if int(ph) != int(h) or int(pr) != int(r):
        return "qc block_id (h,r) mismatch"
    ledger_commitment = str(getattr(qc, "ledger_commitment", "") or "").strip().lower()
    txs_root = str(getattr(qc, "txs_root", "") or "").strip().lower()
    if ledger_commitment:
        if not bid.endswith(f"-C{ledger_commitment}"):
            return "qc ledger commitment does not match block_id"
        try:
            if len(ledger_commitment) != 64 or len(txs_root) != 64:
                raise ValueError
            bytes.fromhex(ledger_commitment)
            bytes.fromhex(txs_root)
        except ValueError:
            return "qc ledger commitment invalid"

    if not voters:
        return "qc voters empty"

    seen: set[str] = set()
    power = 0
    for vid in voters:
        svid = str(vid or "").strip()
        if not svid or svid in seen:
            continue
        seen.add(svid)
        if not vset.is_member(svid):
            return f"qc voter not in validator set: {svid}"
        power += vset.power_of(svid)

    if power < vset.quorum_power():
        return "qc has no quorum"

    if last_qc is not None:
        try:
            lh = int(getattr(last_qc, "height", 0) or 0)
            lr = int(getattr(last_qc, "round", 0) or 0)
            lbid = str(getattr(last_qc, "block_id", "") or "").strip()
        except Exception:
            return "last_qc decode failed"

        if h < lh:
            return "qc height regresses"
        if h == lh:
            if r < lr:
                return "qc round regresses at same height"
            if r == lr and bid != lbid:
                return "qc conflicts at same height/round"

    return None

def _qc_key(qc: Optional[QC]) -> tuple[int, int]:
    if qc is None:
        return (-1, -1)
    try:
        return (int(qc.height), int(qc.round))
    except Exception:
        return (-1, -1)


def _expected_leader_for_hr(*, height: int, round: int, vset: ValidatorSet) -> Optional[str]:
    ids = vset.ordered_ids()
    if not ids:
        return None
    idx = (int(height) - 1 + int(round)) % len(ids)
    return ids[idx]


class ConsensusEngine:
    """
    PR3.3:
      - round timeouts -> round advance
      - lock rules (self-lock after PRECOMMIT; don't vote conflicting blocks at same height)
      - equivocation detection object (record + reject conflicting vote messages)
      - persistence: finalized_height + last_qc across restart

    PR4 (minimal):
      - periodic sync to pull peer tips and fast-forward monotonically when behind
    """

    def __init__(self) -> None:
        self.chain_id = (os.getenv("GLYPHCHAIN_CHAIN_ID", "") or "glyphchain-dev").strip()
        self.node_id = (os.getenv("GLYPHCHAIN_NODE_ID", "") or "dev-node").strip()
        configured_self_val_id = (os.getenv("GLYPHCHAIN_SELF_VAL_ID", "") or "").strip()
        from backend.modules.p2p.network_participation import participation_from_env
        self._network_participation = participation_from_env()
        if self._network_participation.get("enforced"):
            self.self_val_id = (
                configured_self_val_id
                if self._network_participation.get("role") == "validator" else ""
            )
        else:
            self.self_val_id = configured_self_val_id

        self.vset = ValidatorSet.from_env()

        # Portable quorum-finality is enabled only with an operator-pinned
        # validator-set checkpoint.  Ordinary development consensus remains
        # backwards compatible, but cannot claim independent finality.
        self._finality_checkpoint = load_trusted_checkpoint_from_env()
        self._finality_private_key: Optional[Ed25519PrivateKey] = None
        self._finality_config_error: Optional[str] = None
        self.network_id = (os.getenv("GLYPHCHAIN_NETWORK_ID", "") or "devnet").strip()
        if self._finality_checkpoint is not None:
            cp = self._finality_checkpoint.value
            if str(cp["chain_id"]) != self.chain_id or str(cp["network_id"]) != self.network_id:
                raise ValueError("finality checkpoint chain_id/network_id mismatch")
            checkpoint_powers = {
                str(item["validator_id"]): int(item["power"])
                for item in cp["validator_set"]
            }
            if checkpoint_powers != {str(k): int(v) for k, v in self.vset.powers.items()}:
                raise ValueError("finality checkpoint validator set does not match consensus validator set")
            key_hex = str(os.getenv("GLYPHCHAIN_FINALITY_PRIVKEY_HEX", "") or "").strip().lower()
            p2p_key_hex = str(os.getenv("GLYPHCHAIN_P2P_PRIVKEY_HEX", "") or "").strip().lower()
            if key_hex and p2p_key_hex and hmac.compare_digest(key_hex, p2p_key_hex):
                raise ValueError("finality and P2P transport keys must be distinct")
            if self.self_val_id and key_hex:
                try:
                    candidate = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(key_hex))
                    validator = self._finality_checkpoint.validator(self.self_val_id)
                    local_public = base64.b64encode(candidate.public_key().public_bytes(
                        serialization.Encoding.Raw,
                        serialization.PublicFormat.Raw,
                    )).decode("ascii")
                    if validator is None or local_public != str(validator["public_key_base64"]):
                        raise ValueError("local finality key does not match trusted checkpoint")
                    self._finality_private_key = candidate
                except Exception as exc:
                    self._finality_config_error = str(exc)
        if self._network_participation.get("enforced") and self._network_participation.get("role") == "validator":
            if not self.self_val_id:
                raise ValueError("validator participation requires GLYPHCHAIN_SELF_VAL_ID")
            if self._finality_checkpoint is None:
                raise ValueError("validator participation requires a trusted finality checkpoint")
            if (
                str(self._network_participation.get("validator_set_checkpoint_id") or "")
                != self._finality_checkpoint.checkpoint_id
            ):
                raise ValueError("validator participation checkpoint does not match trusted finality checkpoint")

        # config knobs
        self._tick_ms = _bounded_int_env("CONSENSUS_TICK_MS", 50, 1, 600_000)
        self._round_timeout_ms = _bounded_int_env("CONSENSUS_ROUND_TIMEOUT_MS", 1500, 10, 3_600_000)
        self._rebcast_s = float(os.getenv("CONSENSUS_PROPOSAL_REBCAST_S", "0.75") or "0.75")

        # Freeze tick progression briefly after a big jump-finalization (tests inject far-ahead heights)
        self._post_jump_freeze_ms = _bounded_int_env("CONSENSUS_POST_JUMP_FREEZE_MS", 20_000, 0, 3_600_000)
        self._freeze_until_ms: float = 0.0
        self._no_proposal_timeouts: Dict[Tuple[int, int], int] = {}

        self._proposal_seen_ms: Dict[tuple[int, int, str], float] = {}
        self._finality_lat_ms: Deque[float] = deque(
            maxlen=_bounded_int_env("CONSENSUS_FINALITY_LAT_SAMPLES", 64, 8, 10_000)
        )

        # proposal-missing timeout backoff (prevents runaway + keeps liveness)
        self._no_proposal_wait_n = _bounded_int_env("CONSENSUS_NO_PROPOSAL_WAIT_N", 2, 1, 1_000)

        # PR4 sync knobs
        self._sync_every_ms = _bounded_int_env("CONSENSUS_SYNC_EVERY_MS", 1500, 10, 600_000)
        self._max_recovery_blocks = _bounded_int_env(
            "CONSENSUS_MAX_BLOCKS_PER_RECOVERY", 2_048, 1, 10_000,
        )
        self._sync_enabled = _truthy("CONSENSUS_SYNC_ENABLE", True)
        self._last_sync_ms: float = 0.0

        self._lock = threading.Lock()
        self._sync_policy = SyncPolicy()
        self._sync_height_fails: dict[int, int] = {}
        self._partition_recovery = PartitionRecoveryStore.from_env(
            chain_id=self.chain_id,
            node_id=self.node_id,
        )
        self._protocol_upgrade = ProtocolUpgradeStore.from_env(
            chain_id=self.chain_id, node_id=self.node_id,
        )

        # proposal/vote storage
        self._proposals: Dict[Tuple[int, int], Proposal] = {}  # (h,r) -> Proposal
        self._votes: Dict[Tuple[int, int, VoteType, str], Set[str]] = {}  # (h,r,type,block_id) -> voters
        self._finality_vote_evidence: Dict[Tuple[int, int, str, str], str] = {}

        # PR6.2: round-hint fork-choice memory
        self._round_hint: Dict[int, int] = {}  # height -> max observed round

        # anti-spam / idempotency for our own outbound votes
        self._sent: Set[Tuple[int, int, VoteType, str, str]] = set()  # (h,r,type,block_id,self_val_id)

        # equivocation detection: key=(h,r,voter,vote_type) -> block_id previously seen
        self._seen_votes: Dict[Tuple[int, int, str, VoteType], str] = {}
        self._evidence: list[Dict[str, Any]] = []

        # self lock (Tendermint-ish minimal): once we PRECOMMIT, we lock that block for the height
        self._lock_height: int = 0
        self._lock_round: int = -1
        self._lock_block_id: Optional[str] = None

        # rebroadcast throttle per (h,r)
        self._last_bcast: Dict[Tuple[int, int], float] = {}

        # PR4.2: block fill guard
        self._syncing_blocks: bool = False

        # persisted state (restart-safe)
        ps = load_state()
        self._finalized_height: int = int(ps.finalized_height or 0)
        self._last_qc: Optional[QC] = None
        if isinstance(ps.last_qc, dict):
            try:
                self._last_qc = QC(**ps.last_qc)  # type: ignore[arg-type]
            except Exception:
                self._last_qc = None
        if self._last_qc is not None and self._finality_checkpoint is not None:
            persisted_finality_error = self._qc_finality_error(self._last_qc)
            if persisted_finality_error:
                raise ValueError(f"persisted consensus state is not trust-anchored: {persisted_finality_error}")
        self._recent_qcs: Deque[QC] = deque(
            maxlen=_bounded_int_env("CONSENSUS_RECENT_QC_LIMIT", 64, 8, 10_000)
        )
        if self._last_qc is not None:
            self._recent_qcs.append(self._last_qc)

        # round state should never start behind finalized_height
        self._cur_height: int = self._finalized_height + 1
        self._cur_round: int = int(ps.round or 0) if int(ps.finalized_height or 0) > 0 else 0
        self._round_started_ms: float = _now_ms()

        # Ensure chain_sim in-memory cache is populated after restart so get_block(h) returns dict, not int sentinel.
        try:
            from backend.modules.chain_sim.chain_sim_ledger import replay_state_from_db
            replay_state_from_db()
        except Exception:
            pass

        # background driver task
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_evt: Optional[asyncio.Event] = None

    # -------------------------
    # Introspection
    # -------------------------
    def _partition_recovery_status(self) -> Dict[str, Any]:
        try:
            state = self._partition_recovery.status()
            return {
                **state,
                "journal_valid": self._partition_recovery.verify_journal(),
                "state_readable": True,
            }
        except PartitionRecoveryError as exc:
            # A corrupt recovery record is itself a safety condition.  Do not
            # silently replace it with a healthy default.
            return {
                "schema_version": "glyphchain.partition-recovery.v1",
                "phase": PHASE_SAFETY_HALT,
                "reason": "partition_recovery_state_invalid",
                "last_error": str(exc),
                "journal_valid": False,
                "state_readable": False,
            }

    def _partition_recovery_halted(self) -> bool:
        return self._partition_recovery_status().get("phase") == PHASE_SAFETY_HALT

    def _protocol_upgrade_status(self, *, next_height: Optional[int] = None) -> Dict[str, Any]:
        try:
            peer_views: list[dict[str, Any]] = []
            load_peers_from_env()
            for peer in list_peers():
                if not bool(getattr(peer, "hello_ok", False)):
                    continue
                peer_views.append({
                    "validator_id": str(getattr(peer, "val_id", "") or ""),
                    "protocol": dict(getattr(peer, "protocol", {}) or {}),
                })
            with self._lock:
                height = int(next_height or self._cur_height)
            result = self._protocol_upgrade.assess(
                next_height=height,
                validator_powers=dict(self.vset.powers),
                self_validator_id=self.self_val_id,
                peer_advertisements=peer_views,
            )
            return {
                **result,
                "journal_valid": self._protocol_upgrade.verify_journal(),
                "state_readable": True,
            }
        except (ProtocolUpgradeError, OSError, ValueError) as exc:
            return {
                "phase": "UPGRADE_HALT",
                "consensus_allowed": False,
                "reason": "protocol_upgrade_state_invalid",
                "last_error": str(exc),
                "journal_valid": False,
                "state_readable": False,
            }

    def _set_partition_recovery_phase(self, phase: str, *, reason: str, **fields: Any) -> Dict[str, Any]:
        try:
            current = self._partition_recovery.status()
            if current.get("phase") == PHASE_SAFETY_HALT and phase != PHASE_SAFETY_HALT:
                return current
            comparable = {"phase": phase, "reason": reason, **fields}
            if all(current.get(key) == value for key, value in comparable.items()):
                return current
            return self._partition_recovery.transition(phase, reason=reason, **fields)
        except PartitionRecoveryError:
            return self._partition_recovery_status()

    def clear_partition_safety_halt(
        self,
        *,
        halt_id: str,
        operator_id: str,
        reason: str,
        confirmation: str,
    ) -> Dict[str, Any]:
        return self._partition_recovery.clear_safety_halt(
            halt_id=halt_id,
            operator_id=operator_id,
            reason=reason,
            confirmation=confirmation,
        )

    def sign_validator_governance_approval(self, proposal: Dict[str, Any]) -> Dict[str, str]:
        """Sign a checkpoint transition in a domain separate from finality votes."""
        if not self.self_val_id or not self.vset.is_member(self.self_val_id):
            raise ValueError("local node is not an active validator")
        if self._finality_private_key is None:
            raise ValueError("local validator governance signing key is unavailable")
        return sign_validator_governance_approval(
            proposal,
            validator_id=self.self_val_id,
            private_key=self._finality_private_key,
        )

    def apply_verified_snapshot_finality(
        self,
        *,
        snapshot_summary: Dict[str, Any],
        finality_certificate: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Persist a separately trust-anchored snapshot tip after installation.

        Snapshot verification and atomic database installation occur before this
        call.  This method revalidates the certificate against the engine's own
        trust anchor and binds the installed tip block before changing consensus
        state.  It is the explicit large-gap partition-recovery path.
        """
        if self._partition_recovery_halted():
            raise ValueError("partition recovery safety halt must be explicitly cleared before snapshot installation")
        if self._finality_checkpoint is None:
            raise ValueError("verified snapshot finality requires a trusted validator checkpoint")
        ledger = snapshot_summary.get("ledger") if isinstance(snapshot_summary.get("ledger"), dict) else {}
        height = int(ledger.get("height") or 0)
        certificate = dict(finality_certificate or {})
        voters = [
            str(item.get("validator_id") or "").strip()
            for item in list(certificate.get("votes") or [])
            if isinstance(item, dict) and str(item.get("validator_id") or "").strip()
        ]
        qc = QC(
            height=height,
            round=int(certificate.get("round") or 0),
            vote_type="PRECOMMIT",
            block_id=str(certificate.get("block_id") or ""),
            voters=voters,
            ts_ms=_now_ms(),
            quorum_finality_certificate=certificate,
            trusted_validator_set_root=self._finality_checkpoint.validator_set_root,
            validator_set_checkpoint_id=self._finality_checkpoint.checkpoint_id,
            ledger_commitment=str(certificate.get("ledger_commitment") or "") or None,
            txs_root=str(certificate.get("txs_root") or "") or None,
        )
        structural = _validate_qc_structural_or_error(qc, vset=self.vset, last_qc=None, expect_height=height)
        if structural:
            raise ValueError(structural)
        finality_error = self._qc_finality_error(qc)
        if finality_error:
            raise ValueError(finality_error)
        block = self._read_local_block(height)
        if block is None:
            raise ValueError("verified snapshot tip block is not installed")
        block_error = self._verify_recovery_block(block, height=height, tip_qc=qc)
        if block_error:
            raise ValueError(block_error)

        with self._lock:
            old_fh = int(self._finalized_height)
            old_qc = self._last_qc
        if height < old_fh:
            raise ValueError("verified snapshot would regress finalized height")
        if height == old_fh and old_qc is not None and str(old_qc.block_id) != str(qc.block_id):
            classification = classify_validated_views(
                [{"height": height, "round": int(qc.round), "block_id": str(qc.block_id)}],
                local_height=old_fh,
                local_block_id=str(old_qc.block_id),
            )
            state = self._set_partition_recovery_phase(
                PHASE_SAFETY_HALT,
                reason="verified_snapshot_conflicts_with_local_finality",
                local_finalized_height=old_fh,
                target_finalized_height=height,
                target_block_id=str(qc.block_id),
                conflict_digest=str(classification.get("conflict_digest") or ""),
                conflicting_heights=[height],
                last_error="verified snapshot conflicts with local finalized block",
            )
            raise ValueError(f"verified snapshot conflicts with local finality; halt_id={state.get('halt_id')}")

        with self._lock:
            if height > int(self._finalized_height):
                self._finalized_height = height
                self._last_qc = qc
                self._retain_finality_qc_locked(qc)
                self._cur_height = height + 1
                self._cur_round = 0
                self._round_started_ms = _now_ms()
        save_state(
            int(self._finalized_height),
            self._last_qc.model_dump() if self._last_qc else None,
            round=0,
        )
        recovery = self._set_partition_recovery_phase(
            PHASE_HEALTHY,
            reason="verified_snapshot_installed_and_finality_applied",
            local_finalized_height=height,
            valid_view_count=1,
            installed_snapshot_id=str(snapshot_summary.get("snapshot_id") or ""),
        )
        return {
            "applied": height > old_fh,
            "old_finalized_height": old_fh,
            "finalized_height": int(self._finalized_height),
            "block_id": str(qc.block_id),
            "partition_recovery": recovery,
        }

    def status(self) -> Dict[str, Any]:
        def _pct(vals: list[float], p: float) -> Optional[float]:
            if not vals:
                return None
            s = sorted(vals)
            n = len(s)
            if n == 1:
                return float(s[0])
            idx = int(round((p / 100.0) * (n - 1)))
            idx = max(0, min(n - 1, idx))
            return float(s[idx])

        with self._lock:
            h = int(self._cur_height)
            r = int(self._cur_round)
            fh = int(self._finalized_height)
            have = (h, r) in self._proposals

            lock = {
                "height": int(self._lock_height),
                "round": int(self._lock_round),
                "block_id": self._lock_block_id,
            }
            evidence_tail = list(self._evidence)[-10:]

            prop = self._proposals.get((h, r))
            prop_fp = _proposal_fingerprint(prop) if prop is not None else None
            prop_bid = getattr(prop, "block_id", None) if prop is not None else None

            lat = list(self._finality_lat_ms)
            last_qc = (self._last_qc.model_dump() if self._last_qc else None)
            recent_qcs = [qc.model_dump() for qc in self._recent_qcs]
            latest_finality_certificate = (
                getattr(self._last_qc, "quorum_finality_certificate", None)
                if self._last_qc is not None else None
            )

        last_lat = float(lat[-1]) if lat else None

        leader = self.leader_for(h, r)

        return {
            "ok": True,
            "chain_id": self.chain_id,
            "node_id": self.node_id,
            "self_val_id": self.self_val_id,
            "network_participation": dict(self._network_participation),
            "validators": self.vset.ordered_ids(),
            "finalized_height": fh,
            "height": h,
            "round": r,
            "leader": leader,
            "have_proposal": have,
            "proposal_block_id": prop_bid,
            "proposal_fp": prop_fp,
            "lock": lock,
            "evidence_tail": evidence_tail,
            "net_ok": _NET_OK,
            "net_err": (_NET_ERR if not _NET_OK else None),
            "last_qc": last_qc,
            "recent_qcs": recent_qcs,
            "quorum_finality": {
                "enabled": self._finality_checkpoint is not None,
                "local_signer_ready": self._finality_private_key is not None,
                "configuration_error": self._finality_config_error,
                "checkpoint_id": (
                    self._finality_checkpoint.checkpoint_id
                    if self._finality_checkpoint is not None else None
                ),
                "trusted_validator_set_root": (
                    self._finality_checkpoint.validator_set_root
                    if self._finality_checkpoint is not None else None
                ),
                "latest_certificate": latest_finality_certificate,
            },
            "partition_recovery": self._partition_recovery_status(),
            "protocol_upgrade": self._protocol_upgrade_status(next_height=h),
            "finality_latency_ms_last": last_lat,
            "finality_latency_ms_p50": _pct(lat, 50.0),
            "finality_latency_ms_p95": _pct(lat, 95.0),
            "finality_latency_ms_samples": int(len(lat)),
        }

    def leader_for(self, height: int, round: int = 0) -> Optional[str]:
        ids = self.vset.ordered_ids()
        if not ids:
            return None
        idx = (int(height) - 1 + int(round)) % len(ids)
        return ids[idx]

    def _ledger_candidate(self, *, height: int) -> tuple[dict[str, Any], dict[str, Any]]:
        """Return the local ledger block and its independently checkable commitment."""
        try:
            from backend.modules.chain_sim.chain_sim_ledger import get_block
            block = get_block(int(height))
        except Exception:
            block = None
        candidate = dict(block or empty_ledger_block(height=int(height)))
        commitment = normalize_ledger_block(candidate, chain_id=self.chain_id, height=int(height))
        return candidate, commitment

    def finality_receipt(self, *, height: int, block_id: str | None = None) -> Dict[str, Any]:
        """Return a finalized QC and its portable certificate, if retained."""
        wanted_height = int(height)
        wanted_block = str(block_id or "").strip()
        with self._lock:
            match = next(
                (
                    qc for qc in reversed(self._recent_qcs)
                    if int(qc.height) == wanted_height
                    and (not wanted_block or str(qc.block_id) == wanted_block)
                ),
                None,
            )
        if match is None:
            return {"ok": False, "found": False, "height": wanted_height}
        certificate = getattr(match, "quorum_finality_certificate", None)
        return {
            "ok": True,
            "found": True,
            "height": wanted_height,
            "block_id": str(match.block_id),
            "qc": match.model_dump(),
            "quorum_finality_certificate": certificate,
            "trusted_validator_set_root": getattr(match, "trusted_validator_set_root", None),
            "validator_set_checkpoint_id": getattr(match, "validator_set_checkpoint_id", None),
            "ledger_commitment": getattr(match, "ledger_commitment", None),
            "txs_root": getattr(match, "txs_root", None),
            "independently_verifiable": bool(
                certificate
                and getattr(match, "trusted_validator_set_root", None)
                and getattr(match, "validator_set_checkpoint_id", None)
            ),
        }

    def _retain_finality_qc_locked(self, qc: QC) -> None:
        """Retain every accepted finalized height, independent of last-QC updates.

        Callers hold ``self._lock``.  This prevents an intermediate finalized
        height from disappearing when concurrent progress advances ``last_qc``
        before status or snapshot export reads the receipt history.
        """
        height = int(qc.height)
        block_id = str(qc.block_id)
        if any(int(item.height) == height and str(item.block_id) == block_id for item in self._recent_qcs):
            return
        self._recent_qcs.append(qc)

    def _preferred_round_for_height_locked(self, *, height: int, fallback_round: int) -> int:
        # assumes self._lock is already held
        h = int(height)
        r = int(fallback_round)
        pref = int(self._round_hint.get(h, r) or r)
        if int(self._cur_height) == h:
            pref = max(pref, int(self._cur_round))
        if self._last_qc is not None and int(getattr(self._last_qc, "height", -1) or -1) == h:
            pref = max(pref, int(getattr(self._last_qc, "round", r) or r))
        return int(pref)

    # -------------------------
    # lifecycle
    # -------------------------

    def start(self) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        if self._task is not None and not self._task.done():
            return
        if self._task is not None and self._task.done():
            self._task = None

        self._stop_evt = asyncio.Event()
        self._task = loop.create_task(self._run(), name="consensus-engine")

    async def stop(self) -> None:
        t = self._task
        ev = self._stop_evt
        if t is None and ev is None:
            return

        self._task = None
        self._stop_evt = None

        if ev is not None:
            ev.set()

        if t is not None:
            try:
                await t
            except Exception:
                pass

    async def _run(self) -> None:
        sleep_s = max(0.01, float(self._tick_ms) / 1000.0)
        while True:
            ev = self._stop_evt
            if ev is not None and ev.is_set():
                return
            try:
                await self.tick()
            except Exception:
                # 🔥 don't hide the reason the engine is dead
                import traceback
                traceback.print_exc()
            await asyncio.sleep(sleep_s)

    # -------------------------
    # quorum helper
    # -------------------------

    def _has_quorum(self, *, height: int, round: int, vote_type: VoteType, block_id: str) -> bool:
        key = (int(height), int(round), vote_type, str(block_id))
        with self._lock:
            voters = self._votes.get(key) or set()
            power = 0
            for v in voters:
                power += self.vset.power_of(v)
        return power >= self.vset.quorum_power()

    # -------------------------
    # round/timeout
    # -------------------------

    def _prune_cached_below_round_for_height(self, *, height: int, min_round: int) -> None:
        hh = int(height)
        mr = int(min_round)

        with self._lock:
            self._sent = {k for k in self._sent if not (int(k[0]) == hh and int(k[1]) < mr)}

            self._last_bcast = {
                k: v for (k, v) in self._last_bcast.items()
                if not (int(k[0]) == hh and int(k[1]) < mr)
            }

            self._seen_votes = {
                k: v for (k, v) in self._seen_votes.items()
                if not (int(k[0]) == hh and int(k[1]) < mr)
            }

            self._finality_vote_evidence = {
                k: v for (k, v) in self._finality_vote_evidence.items()
                if not (int(k[0]) == hh and int(k[1]) < mr)
            }

            self._proposal_seen_ms = {
                k: v for (k, v) in self._proposal_seen_ms.items()
                if not (int(k[0]) == hh and int(k[1]) < mr)
            }

            self._proposals = {
                k: v for (k, v) in self._proposals.items()
                if not (int(k[0]) == hh and int(k[1]) < mr)
            }

            self._votes = {
                k: v for (k, v) in self._votes.items()
                if not (int(k[0]) == hh and int(k[1]) < mr)
            }

            self._no_proposal_timeouts = {
                k: v for (k, v) in self._no_proposal_timeouts.items()
                if not (int(k[0]) == hh and int(k[1]) < mr)
            }

    def _prune_for_height_round(self, *, height: int, round: int) -> None:
        with self._lock:
            self._sent = {k for k in self._sent if k[0] >= height and not (k[0] == height and k[1] < round)}

            self._last_bcast = {
                k: v
                for (k, v) in self._last_bcast.items()
                if k[0] >= height and not (k[0] == height and k[1] < round)
            }

            self._seen_votes = {
                k: v
                for (k, v) in self._seen_votes.items()
                if k[0] >= height and not (k[0] == height and k[1] < round)
            }
            self._finality_vote_evidence = {
                k: v for (k, v) in self._finality_vote_evidence.items()
                if k[0] >= height and not (k[0] == height and k[1] < round)
            }
            self._proposal_seen_ms = {
                k: v for (k, v) in self._proposal_seen_ms.items()
                if k[0] >= height and not (k[0] == height and k[1] < round)
            }
            self._sync_height_fails = {
                h: failures for h, failures in self._sync_height_fails.items()
                if int(h) >= int(height)
            }
            if len(self._evidence) > 2000:
                self._evidence = self._evidence[-1000:]

            self._proposals = {
                k: v
                for (k, v) in self._proposals.items()
                if k[0] >= height and not (k[0] == height and k[1] < round)
            }

            self._votes = {
                k: v
                for (k, v) in self._votes.items()
                if k[0] >= height and not (k[0] == height and k[1] < round)
            }

            # ✅ prune no-proposal timeout counters for past (h,r)
            self._no_proposal_timeouts = {
                k: v
                for (k, v) in self._no_proposal_timeouts.items()
                if k[0] >= height and not (k[0] == height and k[1] < round)
            }

            # PR6.2: prune round hints for past heights
            self._round_hint = {hh: rr for (hh, rr) in self._round_hint.items() if int(hh) >= int(height)}

    def _advance_round(self) -> None:
        with self._lock:
            self._cur_round += 1
            self._round_started_ms = _now_ms()
            h = int(self._cur_height)
            r = int(self._cur_round)
        self._prune_for_height_round(height=h, round=r)

    # --- in ConsensusEngine._advance_height() ---

    def _advance_height(self) -> None:
        with self._lock:
            self._cur_height = int(self._finalized_height) + 1
            self._cur_round = 0
            self._round_started_ms = _now_ms()

            # ✅ Only clear the lock if it refers to a height we have already finalized.
            # This prevents “future lock” (used by PR6 delayed-msgs tests) from being
            # wiped by normal progress at lower heights.

            # PR6.2: drop hints for finalized/past heights
            self._round_hint = {hh: rr for (hh, rr) in self._round_hint.items() if int(hh) >= int(self._cur_height)}

            h = int(self._cur_height)
            r = int(self._cur_round)

        self._prune_for_height_round(height=h, round=r)

    # -------------------------
    # driver
    # -------------------------

    async def tick(self) -> None:
        if not self.self_val_id or not self.vset.is_member(self.self_val_id):
            return

        # ✅ If we just jumped-finalized far ahead, pause tick so last_qc doesn't race past test target.
        with self._lock:
            fu = float(getattr(self, "_freeze_until_ms", 0.0) or 0.0)
        if fu and _now_ms() < fu:
            return

        # PR6.2: apply per-height round hint fork-choice before doing anything else.
        self._maybe_apply_round_hint_current_height()

        with self._lock:
            h = int(self._cur_height)
            r = int(self._cur_round)
            started = float(self._round_started_ms)

        # periodic sync (helps restart/missed windows catch up)
        if self._sync_enabled:
            now = _now_ms()
            do_sync = False
            with self._lock:
                if (now - float(self._last_sync_ms)) >= float(self._sync_every_ms):
                    self._last_sync_ms = now
                    do_sync = True
            if do_sync:
                self._spawn_async(self._sync_once())

        # Recovery polling remains active during a halt, but this node must not
        # propose or vote until a signed administrator explicitly clears the
        # conflicting-finality condition.
        if self._partition_recovery_halted():
            return
        if not self._protocol_upgrade_status(next_height=h).get("consensus_allowed"):
            return

        # --- IMPORTANT: timeout handling must be proposal-aware (prevents runaway rounds) ---
        leader = self.leader_for(h, r)
        if not leader:
            return

        with self._lock:
            proposal = self._proposals.get((h, r))

        if (_now_ms() - started) >= float(self._round_timeout_ms):
            # If we're not leader and we never received the proposal for (h,r),
            # wait a bounded number of timeouts, then advance for liveness.
            if proposal is None and leader != self.self_val_id:
                k = (int(h), int(r))
                with self._lock:
                    cnt = int(self._no_proposal_timeouts.get(k, 0)) + 1
                    self._no_proposal_timeouts[k] = cnt
                    self._round_started_ms = _now_ms()
                    wait_n = int(getattr(self, "_no_proposal_wait_n", 2) or 2)

                if cnt < wait_n:
                    return

                with self._lock:
                    self._no_proposal_timeouts.pop(k, None)

                self._advance_round()
                return

            # normal timeout -> advance round
            with self._lock:
                self._no_proposal_timeouts.pop((int(h), int(r)), None)

            self._advance_round()
            return

            # leader OR we had a proposal: normal timeout -> advance
            self._advance_round()
            return
        # --- END timeout handling ---

        # -------------------------
        # PR6.2: preferred-round fork-choice (tick selection)
        # -------------------------
        with self._lock:
            h = int(self._cur_height)
            r = int(self._cur_round)

        pref_r = self._preferred_round_for_height(height=h, fallback_round=r)

        # if preference moved beyond our current round, jump (and re-read proposal)
        if int(pref_r) > int(r):
            with self._lock:
                self._cur_round = int(pref_r)
                self._round_started_ms = _now_ms()
                r = int(self._cur_round)
            self._prune_for_height_round(height=h, round=r)

        leader = self.leader_for(h, r)
        if not leader:
            return

        with self._lock:
            proposal = self._proposals.get((h, r))

        # If not leader and we don't have preferred-round proposal, abstain
        # (prevents voting/finalizing on stale rounds behind fork-choice).
        if proposal is None and leader != self.self_val_id:
            return

        # if leader, create proposal if absent
        if proposal is None and leader == self.self_val_id:
            ledger_block: dict[str, Any] = {}
            ledger_commitment: dict[str, Any] = {}
            if self._finality_checkpoint is not None:
                ledger_block, ledger_commitment = self._ledger_candidate(height=h)
            block_id = _canon_block_id(
                h,
                r,
                leader,
                ledger_commitment.get("ledger_commitment"),
            )

            try:
                p = Proposal(
                    height=h,
                    round=r,
                    proposer=leader,
                    block_id=block_id,
                    block=ledger_block,
                    ledger_commitment=ledger_commitment.get("ledger_commitment"),
                    txs_root=ledger_commitment.get("txs_root"),
                    ts_ms=_now_ms(),
                )
            except Exception:
                payload = {
                    "height": h,
                    "round": r,
                    "proposer": leader,
                    "block_id": block_id,
                    "block": ledger_block,
                    "ledger_commitment": ledger_commitment.get("ledger_commitment"),
                    "txs_root": ledger_commitment.get("txs_root"),
                    "ts_ms": _now_ms(),
                }
                p = Proposal(**payload)  # type: ignore

            self.handle_proposal(p)
            proposal = p

        with self._lock:
            locked_h = int(self._lock_height)
            locked_r = int(self._lock_round)
            locked_bid = self._lock_block_id

        # ✅ If we’re locked at this height, only force-vote the locked block in the SAME/OLDER round.
        # Higher rounds are allowed to progress (unlock/relock paths).
        if locked_bid is not None and locked_h == h and int(r) <= locked_r:
            target_block_id = str(locked_bid)
        else:
            if proposal is None:
                return
            target_block_id = str(proposal.block_id)

        # rebroadcast proposal throttled (leader only)
        if proposal is not None and leader == self.self_val_id and _NET_OK and broadcast_proposal is not None:
            k = (int(h), int(r))
            now_s = time.time()
            do_send = False
            with self._lock:
                last = self._last_bcast.get(k)
                if last is None or (now_s - last) >= self._rebcast_s:
                    self._last_bcast[k] = now_s
                    do_send = True
            if do_send:
                try:
                    payload = proposal.model_dump() if hasattr(proposal, "model_dump") else dict(proposal)  # type: ignore
                    await broadcast_proposal(
                        chain_id=self.chain_id,
                        from_node_id=self.node_id,
                        from_val_id=self.self_val_id,
                        payload=payload,
                    )
                except Exception:
                    pass

        await self._maybe_send_vote(height=h, round=r, vote_type="PREVOTE", block_id=target_block_id)

        if self._has_quorum(height=h, round=r, vote_type="PREVOTE", block_id=target_block_id):
            await self._maybe_send_vote(height=h, round=r, vote_type="PRECOMMIT", block_id=target_block_id)

    def _qc_monotonicity_error_locked(self, new_qc: "QC") -> Optional[str]:
        """
        Enforce: last_qc never regresses; same (h,r) cannot conflict.
        Caller MUST hold self._lock.
        """
        if self._last_qc is None:
            return None

        # regression?
        if _is_qc_strictly_newer(self._last_qc, new_qc):
            return "qc regressed vs last_qc"

        # same (h,r) conflict?
        if int(new_qc.height) == int(self._last_qc.height) and int(new_qc.round) == int(self._last_qc.round):
            if str(new_qc.block_id) != str(self._last_qc.block_id) or str(new_qc.vote_type) != str(self._last_qc.vote_type):
                return "qc conflict at same (height,round)"

        return None
    # -------------------------
    # inbound handlers
    # -------------------------

    def handle_proposal(self, p: Proposal) -> Dict[str, Any]:
        if self._partition_recovery_halted():
            return {
                "ok": True,
                "accepted": False,
                "ignored": True,
                "reason": "partition recovery safety halt",
            }
        h = _as_int(getattr(p, "height", None), None)
        r = _as_int(getattr(p, "round", None), None)
        proposer = str(getattr(p, "proposer", "") or "").strip()
        block_id = str(getattr(p, "block_id", "") or "").strip()

        if h is None or h <= 0:
            return {"ok": False, "error": "height must be > 0"}
        if not self._protocol_upgrade_status(next_height=h).get("consensus_allowed"):
            return {"ok": True, "accepted": False, "ignored": True, "reason": "protocol upgrade activation halt"}
        if r is None or r < 0:
            return {"ok": False, "error": "round must be >= 0"}
        if not block_id or not proposer:
            return {"ok": False, "error": "block_id and proposer required"}

        exp = self.leader_for(h, r)
        if exp and proposer != exp:
            return {"ok": False, "error": f"bad proposer: expected {exp}, got {proposer}"}

        supplied_commitment = str(getattr(p, "ledger_commitment", "") or "").strip().lower()
        supplied_txs_root = str(getattr(p, "txs_root", "") or "").strip().lower()
        if self._finality_checkpoint is not None and (not supplied_commitment or not supplied_txs_root):
            return {"ok": False, "error": "ledger commitment and transaction root required"}
        if supplied_commitment or supplied_txs_root:
            try:
                checked = normalize_ledger_block(
                    dict(getattr(p, "block", None) or {}),
                    chain_id=self.chain_id,
                    height=int(h),
                )
            except (TypeError, ValueError) as exc:
                return {"ok": False, "error": f"ledger block invalid: {exc}"}
            if checked["ledger_commitment"] != supplied_commitment:
                return {"ok": False, "error": "ledger commitment mismatch"}
            if checked["txs_root"] != supplied_txs_root:
                return {"ok": False, "error": "ledger transaction root mismatch"}

        expected_bid = _canon_block_id(h, r, proposer, supplied_commitment or None)
        if block_id != expected_bid:
            return {"ok": False, "error": f"non-canonical block_id (got={block_id}, want={expected_bid})"}

        # PR6.2: round-hint memory
        self._record_round_hint(height=int(h), round=int(r))

        # --- FUTURE HEIGHT GATE (bounded; allow PR6 delayed-msg locks) ---
        with self._lock:
            curh = int(self._cur_height)
        max_ahead = int(os.getenv("CONSENSUS_FUTURE_HEIGHT_WINDOW", "64") or "64")
        if int(h) > (curh + max_ahead):
            return {"ok": True, "accepted": False, "ignored": True, "reason": "future height"}
        # --- END FUTURE HEIGHT GATE ---

        # ✅ PR6.3: global monotonic invariant — ignore proposals for already-finalized heights
        with self._lock:
            if int(h) <= int(self._finalized_height):
                return {"ok": True, "accepted": False, "ignored": True, "reason": "past height"}

        # ✅ PR6.2: lock conflict gate (same logic as before)
        with self._lock:
            if (
                self._lock_block_id is not None
                and int(self._lock_height) == int(h)
                and str(block_id) != str(self._lock_block_id)
            ):
                if int(r) <= int(self._lock_round):
                    return {"ok": False, "error": "locked on different block_id"}
                # allow higher-round conflicting proposal to be observed

        # ✅ PR6.3: deterministic fork-choice at same (h,r): smallest proposal_fp wins (lexicographic)
        with self._lock:
            existing = self._proposals.get((int(h), int(r)))
            if existing is None:
                self._proposals[(int(h), int(r))] = p
            else:
                fp_old = str(_proposal_fingerprint(existing))
                fp_new = str(_proposal_fingerprint(p))

                if fp_new == fp_old:
                    # identical dup
                    pass
                elif fp_new < fp_old:
                    # new winner replaces old loser (order-independent convergence)
                    self._proposals[(int(h), int(r))] = p
                else:
                    # new loser ignored (idempotent ok)
                    return {"ok": True, "accepted": False, "ignored": True, "reason": "fork_choice_loser"}

        # clear no-proposal timeout marker
        with self._lock:
            self._no_proposal_timeouts.pop((int(h), int(r)), None)

        # PR6.2: stale-round suppression (accept/store but do not act)
        with self._lock:
            eff_pref = int(self._round_hint.get(int(h), int(r)) or int(r))
            if int(self._cur_height) == int(h):
                eff_pref = max(eff_pref, int(self._cur_round))

        if eff_pref > int(r):
            return {"ok": True, "accepted": False, "ignored": True, "reason": "stale round below preferred round"}

        # PR6.2: converge to observed higher round (current-height fast-forward)
        self._maybe_fast_forward_round(height=int(h), round=int(r))

        # schedule our prevote attempt (idempotent via _sent)
        self._spawn_async(
            self._maybe_send_vote(height=int(h), round=int(r), vote_type="PREVOTE", block_id=str(block_id))
        )

        out: Dict[str, Any] = {"ok": True, "accepted": True}

        # ✅ #6.2: record proposal seen timestamp (bounded)
        if isinstance(out, dict) and out.get("ok") is True and out.get("accepted", True):
            try:
                hh = int(getattr(p, "height", 0) or 0)
                rr = int(getattr(p, "round", 0) or 0)
                bid = str(getattr(p, "block_id", "") or "")
                if hh > 0 and bid:
                    with self._lock:
                        self._proposal_seen_ms[(hh, rr, bid)] = _now_ms()
                        if len(self._proposal_seen_ms) > 8192:
                            try:
                                self._proposal_seen_ms.pop(next(iter(self._proposal_seen_ms)))
                            except Exception:
                                pass
            except Exception:
                pass

        return out


    def handle_vote(self, v: Vote) -> Dict[str, Any]:
        if self._partition_recovery_halted():
            return {
                "ok": True,
                "accepted": False,
                "ignored": True,
                "reason": "partition recovery safety halt",
                "finalized": False,
                "finalized_height": int(self._finalized_height),
            }
        h = _as_int(getattr(v, "height", None), None)
        r = _as_int(getattr(v, "round", None), None)
        voter = str(getattr(v, "voter", "") or "").strip()
        vote_type = getattr(v, "vote_type", None)
        block_id = str(getattr(v, "block_id", "") or "").strip()
        ledger_commitment = str(getattr(v, "ledger_commitment", "") or "").strip().lower()
        txs_root = str(getattr(v, "txs_root", "") or "").strip().lower()

        if h is None or h <= 0:
            return {"ok": False, "error": "height must be > 0"}
        if not self._protocol_upgrade_status(next_height=h).get("consensus_allowed"):
            return {"ok": True, "accepted": False, "ignored": True, "reason": "protocol upgrade activation halt", "finalized": False, "finalized_height": int(self._finalized_height)}
        if r is None or r < 0:
            return {"ok": False, "error": "round must be >= 0"}
        if not block_id or not voter:
            return {"ok": False, "error": "block_id and voter required"}
        if vote_type not in ("PREVOTE", "PRECOMMIT"):
            return {"ok": False, "error": "bad vote_type"}
        if not self.vset.is_member(voter):
            return {"ok": False, "error": f"voter not in validator set: {voter}"}

        # ✅ PR6.1: reject structurally-impossible votes (prevents “vote→QC poison” at the source)
        exp_leader = self.leader_for(int(h), int(r))
        if not exp_leader:
            return {"ok": False, "error": "no leader (empty validator set)"}
        if self._finality_checkpoint is not None and (not ledger_commitment or not txs_root):
            return {"ok": False, "error": "vote ledger commitment and transaction root required"}
        exp_bid = _canon_block_id(int(h), int(r), str(exp_leader), ledger_commitment or None)
        if block_id != exp_bid:
            return {"ok": False, "error": f"non-canonical block_id (got={block_id}, want={exp_bid})"}
        if ledger_commitment or txs_root:
            with self._lock:
                matching_proposal = self._proposals.get((int(h), int(r)))
            if matching_proposal is None:
                return {"ok": False, "error": "content-bound vote requires matching proposal"}
            if (
                str(getattr(matching_proposal, "block_id", "") or "") != block_id
                or str(getattr(matching_proposal, "ledger_commitment", "") or "") != ledger_commitment
                or str(getattr(matching_proposal, "txs_root", "") or "") != txs_root
            ):
                return {"ok": False, "error": "vote ledger commitment does not match proposal"}

        finality_signature: str | None = None
        if vote_type == "PRECOMMIT" and self._finality_checkpoint is not None:
            supplied_root = str(getattr(v, "finality_validator_set_root", "") or "")
            supplied_checkpoint = str(getattr(v, "finality_checkpoint_id", "") or "")
            finality_signature = str(getattr(v, "finality_signature_base64", "") or "")
            if not finality_signature:
                return {"ok": False, "error": "precommit finality signature required"}
            if supplied_root != self._finality_checkpoint.validator_set_root:
                return {"ok": False, "error": "precommit finality validator-set root mismatch"}
            if supplied_checkpoint != self._finality_checkpoint.checkpoint_id:
                return {"ok": False, "error": "precommit finality checkpoint mismatch"}
            validator = self._finality_checkpoint.validator(voter)
            context = self._finality_certificate_context(
                height=int(h),
                round=int(r),
                block_id=block_id,
                ledger_commitment=ledger_commitment,
                txs_root=txs_root,
            )
            if validator is None or not verify_finality_vote(
                context,
                validator=validator,
                signature_base64=finality_signature,
            ):
                return {"ok": False, "error": "precommit finality signature invalid"}

        # PR6.2: remember we've seen (h,r) so we can start at r when we reach height h.
        self._record_round_hint(height=int(h), round=int(r))

        # --- FUTURE HEIGHT GATE (bounded; allow PR6 delayed-msg locks) ---
        with self._lock:
            curh = int(self._cur_height)

        max_ahead = int(os.getenv("CONSENSUS_FUTURE_HEIGHT_WINDOW", "64") or "64")
        if int(h) > (curh + max_ahead):
            return {"ok": True, "accepted": False, "ignored": True, "reason": "future height"}
        # --- END FUTURE HEIGHT GATE ---

        # ✅ PR6.3: global monotonic invariant — ignore votes for already-finalized heights
        with self._lock:
            if int(h) <= int(self._finalized_height):
                return {"ok": True, "accepted": False, "ignored": True, "reason": "past height"}

        # ✅ If we're in a post-jump freeze window, don't allow advancing finalized height further.
        with self._lock:
            fu = float(getattr(self, "_freeze_until_ms", 0.0) or 0.0)
            local_fh = int(getattr(self, "_finalized_height", 0) or 0)

        if fu and _now_ms() < fu and int(h) > int(local_fh):
            return {"ok": True, "accepted": False, "ignored": True, "reason": "freeze window"}

        # PR6.2: if this vote is below our preferred round for this height, accept but ignore it
        with self._lock:
            eff_pref = int(self._round_hint.get(int(h), int(r)) or int(r))
            if int(self._cur_height) == int(h):
                eff_pref = max(eff_pref, int(self._cur_round))

        if eff_pref > int(r):
            return {"ok": True, "accepted": False, "ignored": True, "reason": "stale round below preferred round"}

        # ✅ PR6 gate: converge to observed higher round
        self._maybe_fast_forward_round(height=int(h), round=int(r))

        # ✅ Under lock: reject votes for a conflicting value if we don't even have a matching proposal
        with self._lock:
            if (
                self._lock_block_id is not None
                and int(self._lock_height) == int(h)
                and str(block_id) != str(self._lock_block_id)
            ):
                prop = self._proposals.get((int(h), int(r)))
                prop_bid = str(getattr(prop, "block_id", "") or "") if prop is not None else ""
                if prop is None or prop_bid != str(block_id):
                    return {"ok": False, "error": "locked: no matching proposal for this vote"}

        persist = False
        qc_out: Optional[QC] = None
        finalized = False
        quorum_reached = False

        # equivocation detection: (h,r,voter,vote_type) must not vote two different block_ids
        ev_key = (int(h), int(r), str(voter), vote_type)
        with self._lock:
            prev_bid = self._seen_votes.get(ev_key)
            if prev_bid is not None and str(prev_bid) != block_id:
                proof = {
                    "type": "equivocation",
                    "height": int(h),
                    "round": int(r),
                    "voter": str(voter),
                    "vote_type": str(vote_type),
                    "prev_block_id": str(prev_bid),
                    "new_block_id": str(block_id),
                    "ts_ms": _now_ms(),
                }
                if len(self._evidence) < 2_000:
                    self._evidence.append(proof)
                return {"ok": False, "error": "equivocation detected", "equivocation": True, "proof": proof}
            if prev_bid is None:
                self._seen_votes[ev_key] = str(block_id)

        key = (int(h), int(r), vote_type, str(block_id))
        now_ms = float(getattr(v, "ts_ms", 0.0) or 0.0) or _now_ms()

        with self._lock:
            locked_bid = str(self._lock_block_id) if self._lock_block_id is not None else None
            locked_r = int(self._lock_round)

            if locked_bid is not None and int(self._lock_height) == int(h) and str(block_id) != locked_bid:
                if int(r) <= locked_r:
                    return {"ok": False, "error": "locked on different block_id"}

                if vote_type == "PRECOMMIT":
                    pv_key = (int(h), int(r), "PREVOTE", str(block_id))
                    pv_set = self._votes.get(pv_key) or set()
                    pv_power = 0
                    for vv in pv_set:
                        pv_power += self.vset.power_of(vv)
                    if pv_power < self.vset.quorum_power():
                        return {"ok": False, "error": "precommit without prevote quorum"}

            s = self._votes.get(key)
            if s is None:
                s = set()
                self._votes[key] = s
            s.add(str(voter))
            if vote_type == "PRECOMMIT" and finality_signature:
                self._finality_vote_evidence[(int(h), int(r), str(block_id), str(voter))] = finality_signature

            power = 0
            for vv in s:
                power += self.vset.power_of(vv)
            quorum_reached = power >= self.vset.quorum_power()

            # relock on higher-round prevote quorum for different value
            if vote_type == "PREVOTE" and quorum_reached:
                if locked_bid is not None and int(self._lock_height) == int(h) and str(block_id) != locked_bid:
                    if int(r) > locked_r:
                        self._lock_height = int(h)
                        self._lock_round = int(r)
                        self._lock_block_id = str(block_id)

            if vote_type == "PRECOMMIT" and quorum_reached:
                old_fh = int(self._finalized_height)

                pref = self._preferred_round_for_height_locked(height=int(h), fallback_round=int(r))
                if int(r) < int(pref):
                    return {"ok": True, "accepted": False, "ignored": True, "reason": "stale round below preferred round"}

                # finalized_height monotonic (only advance)
                if int(h) > int(self._finalized_height):
                    finality_certificate = self._build_quorum_finality_certificate_locked(
                        height=int(h),
                        round=int(r),
                        block_id=str(block_id),
                        voters=sorted(list(s)),
                        ledger_commitment=ledger_commitment,
                        txs_root=txs_root,
                    )
                    qc_out = QC(
                        height=int(h),
                        round=int(r),
                        vote_type="PRECOMMIT",
                        block_id=str(block_id),
                        voters=sorted(list(s)),
                        ts_ms=now_ms,
                        quorum_finality_certificate=finality_certificate,
                        trusted_validator_set_root=(
                            self._finality_checkpoint.validator_set_root
                            if self._finality_checkpoint is not None else None
                        ),
                        validator_set_checkpoint_id=(
                            self._finality_checkpoint.checkpoint_id
                            if self._finality_checkpoint is not None else None
                        ),
                        ledger_commitment=ledger_commitment or None,
                        txs_root=txs_root or None,
                    )

                    err = _validate_qc_structural_or_error(qc=qc_out, vset=self.vset, last_qc=self._last_qc)
                    if err:
                        return {"ok": False, "error": f"qc invalid: {err}"}

                    # ✅ PR6.3: monotonic last_qc invariant (reject regressions/conflicts)
                    err2 = self._qc_monotonicity_error_locked(qc_out)
                    if err2:
                        return {"ok": False, "error": err2}

                    self._finalized_height = int(h)
                    finalized = True
                    self._retain_finality_qc_locked(qc_out)

                    # ✅ only set last_qc if strictly newer
                    if self._last_qc is None or _is_qc_strictly_newer(qc_out, self._last_qc):
                        self._last_qc = qc_out
                    persist = True

                    # ✅ #6.2: finality latency window (cheap; we are already under self._lock)
                    try:
                        k = (int(h), int(r), str(block_id))
                        now = _now_ms()
                        seen = float(self._proposal_seen_ms.get(k, now) or now)
                        self._finality_lat_ms.append(max(0.0, now - seen))
                        self._proposal_seen_ms.pop(k, None)  # optional cleanup
                    except Exception:
                        pass

                    if int(h) > int(old_fh) + 1:
                        self._freeze_until_ms = max(
                            float(self._freeze_until_ms or 0.0),
                            _now_ms() + float(self._post_jump_freeze_ms),
                        )

        # outside lock: reactive prevote + precommit sends
        if vote_type == "PREVOTE" and voter != self.self_val_id:
            self._spawn_async(
                self._maybe_send_vote(height=int(h), round=int(r), vote_type="PREVOTE", block_id=str(block_id))
            )

        if vote_type == "PREVOTE" and quorum_reached:
            self._spawn_async(
                self._maybe_send_vote(height=int(h), round=int(r), vote_type="PRECOMMIT", block_id=str(block_id))
            )

        if persist:
            try:
                save_state(
                    int(self._finalized_height),
                    self._last_qc.model_dump() if self._last_qc else None,
                    round=int(r),
                )
            except Exception:
                pass

            try:
                with self._lock:
                    finalized_proposal = self._proposals.get((int(h), int(r)))
                proposed_block = dict(getattr(finalized_proposal, "block", None) or {})
                if proposed_block.get("txs"):
                    self._import_block_into_chain_sim_db(proposed_block)
            except Exception:
                pass

            try:
                self._persist_finalized_block_shell(
                    height=int(h),
                    block_id=str(block_id),
                    qc=qc_out,
                    created_at_ms=int(now_ms),
                )
            except Exception:
                pass

            self._advance_height()

        return {
            "ok": True,
            "accepted": True,
            "finalized": finalized,
            "finalized_height": int(self._finalized_height),
            "qc": (qc_out.model_dump() if qc_out else None),
            "quorum_finality_certificate": (
                getattr(qc_out, "quorum_finality_certificate", None) if qc_out else None
            ),
            "trusted_validator_set_root": (
                getattr(qc_out, "trusted_validator_set_root", None) if qc_out else None
            ),
        }

    def _finality_certificate_context(
        self,
        *,
        height: int,
        round: int,
        block_id: str,
        ledger_commitment: str | None = None,
        txs_root: str | None = None,
    ) -> dict[str, Any]:
        if self._finality_checkpoint is None:
            raise ValueError("finality checkpoint is not configured")
        return build_finality_certificate(
            chain_id=self.chain_id,
            network_id=self.network_id,
            height=int(height),
            round=int(round),
            block_id=str(block_id),
            validator_set=self._finality_checkpoint.value["validator_set"],
            votes=[],
            checkpoint_id=self._finality_checkpoint.checkpoint_id,
            ledger_commitment=ledger_commitment,
            txs_root=txs_root,
        )

    def _build_quorum_finality_certificate_locked(
        self,
        *,
        height: int,
        round: int,
        block_id: str,
        voters: list[str],
        ledger_commitment: str | None = None,
        txs_root: str | None = None,
    ) -> dict[str, Any] | None:
        if self._finality_checkpoint is None:
            return None
        votes = []
        for voter in voters:
            signature = self._finality_vote_evidence.get((height, round, block_id, voter))
            if signature:
                votes.append({"validator_id": voter, "signature_base64": signature})
        certificate = build_finality_certificate(
            chain_id=self.chain_id,
            network_id=self.network_id,
            height=height,
            round=round,
            block_id=block_id,
            validator_set=self._finality_checkpoint.value["validator_set"],
            votes=votes,
            checkpoint_id=self._finality_checkpoint.checkpoint_id,
            ledger_commitment=ledger_commitment,
            txs_root=txs_root,
        )
        verification = verify_finality_certificate(
            certificate,
            trusted_validator_set_root=self._finality_checkpoint.validator_set_root,
            expected_chain_id=self.chain_id,
            expected_height=height,
            expected_block_id=block_id,
            expected_ledger_commitment=ledger_commitment,
            expected_txs_root=txs_root,
        )
        if not verification.get("valid") or verification.get("trust_anchor_verified") is not True:
            raise ValueError("quorum finality certificate could not be verified")
        return certificate

    def _qc_finality_error(self, qc: QC) -> str | None:
        """Enforce portable finality on every QC when a trust anchor is active."""
        if self._finality_checkpoint is None:
            return None
        certificate = getattr(qc, "quorum_finality_certificate", None)
        if not isinstance(certificate, dict):
            return "qc missing required quorum finality certificate"
        if not getattr(qc, "ledger_commitment", None) or not getattr(qc, "txs_root", None):
            return "qc missing ledger commitment"
        if str(getattr(qc, "trusted_validator_set_root", "") or "") != self._finality_checkpoint.validator_set_root:
            return "qc trusted validator-set root mismatch"
        if str(getattr(qc, "validator_set_checkpoint_id", "") or "") != self._finality_checkpoint.checkpoint_id:
            return "qc validator-set checkpoint mismatch"
        result = verify_finality_certificate(
            certificate,
            trusted_validator_set_root=self._finality_checkpoint.validator_set_root,
            expected_chain_id=self.chain_id,
            expected_height=int(qc.height),
            expected_block_id=str(qc.block_id),
            expected_ledger_commitment=str(getattr(qc, "ledger_commitment", "") or "") or None,
            expected_txs_root=str(getattr(qc, "txs_root", "") or "") or None,
        )
        if not result.get("valid") or result.get("trust_anchor_verified") is not True:
            return "qc quorum finality certificate invalid"
        return None

    # -------------------------
    # PR4: sync helpers
    # -------------------------

    def _persist_finalized_block_shell(
        self,
        *,
        height: int,
        block_id: str,
        qc: Optional[QC],
        created_at_ms: int,
    ) -> None:
        """
        Persist a minimal block so /api/p2p/block_req can serve it.
        This does NOT try to reconstruct txs/state; it’s a shell block with header metadata.
        """
        h = int(height or 0)
        if h <= 0:
            return

        cam = int(created_at_ms or 0) or int(_now_ms())

        header: Dict[str, Any] = {
            "chain_id": self.chain_id,
            "height": h,
            "consensus_block_id": str(block_id or f"h{h}-unknown"),
            "finalized": True,
            "finalized_at_ms": cam,
        }
        if qc is not None:
            try:
                header["qc"] = qc.model_dump() if hasattr(qc, "model_dump") else dict(qc)  # type: ignore
                if getattr(qc, "ledger_commitment", None):
                    header["ledger_commitment"] = str(qc.ledger_commitment)
                if getattr(qc, "txs_root", None):
                    header["txs_root"] = str(qc.txs_root)
            except Exception:
                header["qc"] = None

        try:
            from backend.modules.chain_sim.chain_sim_ledger import (
                persist_begin_block,
                persist_commit_block,
            )
        except Exception:
            return

        # idempotent-ish: begin may fail if exists; commit patches header/checkpoint
        try:
            persist_begin_block(h, cam, header=header)
        except Exception:
            pass
        try:
            persist_commit_block(h, header)
        except Exception:
            pass

    def _persist_finalized_shell_range(
        self,
        *,
        from_height: int,
        to_height: int,
        tip_block_id: str,
        tip_qc: Optional[QC],
        tip_created_at_ms: int,
    ) -> None:
        """
        Ensure every height in [from..to] has at least a shell block in DB.
        Tip gets QC + block_id; intermediate heights get placeholders.
        """
        a = int(from_height or 0)
        b = int(to_height or 0)
        if a <= 0 or b <= 0 or a > b:
            return

        # keep it bounded just in case someone reports a giant jump
        max_n = int(os.getenv("CONSENSUS_SYNC_SHELL_MAX", "512") or "512")
        if (b - a + 1) > max_n:
            a = b - max_n + 1

        for h in range(a, b + 1):
            if h == b:
                self._persist_finalized_block_shell(
                    height=h,
                    block_id=str(tip_block_id or f"h{h}-unknown"),
                    qc=tip_qc,
                    created_at_ms=int(tip_created_at_ms or _now_ms()),
                )
            else:
                self._persist_finalized_block_shell(
                    height=h,
                    block_id=f"h{h}-unknown",
                    qc=None,
                    created_at_ms=int(_now_ms()),
                )

        # IMPORTANT: make chain_sim serve dicts immediately (fixes "int height" returns)
        try:
            from backend.modules.chain_sim.chain_sim_ledger import replay_state_from_db
            replay_state_from_db()
        except Exception:
            pass

    def _have_block_local(self, height: int) -> bool:
        h = int(height or 0)
        if h <= 0:
            return False

        try:
            from backend.modules.chain_sim.chain_sim_ledger import get_block as _get_block
            b = _get_block(h)
            if isinstance(b, dict):
                return True
        except Exception:
            pass

        # If not in memory yet, see if it already exists in sqlite
        try:
            from backend.modules.chain_sim.chain_sim_ledger import load_all_blocks
            rows = load_all_blocks()
            for r in rows:
                if int(r.get("height") or 0) == h:
                    return True
        except Exception:
            pass

        return False

    def _read_local_block(self, height: int) -> Optional[Dict[str, Any]]:
        h = int(height or 0)
        if h <= 0:
            return None
        try:
            from backend.modules.chain_sim.chain_sim_ledger import get_block, replay_ledger_only_from_db
            block = get_block(h)
            if not isinstance(block, dict):
                replay_ledger_only_from_db()
                block = get_block(h)
            return dict(block) if isinstance(block, dict) else None
        except Exception:
            return None

    def _verify_recovery_block(self, block: Dict[str, Any], *, height: int, tip_qc: Optional[QC] = None) -> Optional[str]:
        try:
            commitment = normalize_ledger_block(block, chain_id=self.chain_id, height=int(height))
        except (TypeError, ValueError) as exc:
            return f"ledger block invalid: {exc}"
        if tip_qc is not None:
            expected_commitment = str(getattr(tip_qc, "ledger_commitment", "") or "").strip().lower()
            expected_root = str(getattr(tip_qc, "txs_root", "") or "").strip().lower()
            if expected_commitment and commitment["ledger_commitment"] != expected_commitment:
                return "tip ledger commitment mismatch"
            if expected_root and commitment["txs_root"] != expected_root:
                return "tip transaction root mismatch"
        return None

    def _local_recovery_range_status(self, from_h: int, to_h: int, *, tip_qc: Optional[QC] = None) -> Dict[str, Any]:
        missing: list[int] = []
        invalid: list[dict[str, Any]] = []
        a = int(from_h or 0)
        b = int(to_h or 0)
        if a <= 0 or b <= 0 or a > b:
            return {"complete": False, "missing": [], "invalid": [], "error": "bad height range"}
        if b - a + 1 > self._max_recovery_blocks:
            return {"complete": False, "missing": [], "invalid": [], "error": "recovery height range exceeds limit"}
        for height in range(a, b + 1):
            block = self._read_local_block(height)
            if block is None:
                missing.append(height)
                continue
            error = self._verify_recovery_block(
                block,
                height=height,
                tip_qc=tip_qc if height == b else None,
            )
            if error:
                invalid.append({"height": height, "error": error})
        return {
            "complete": not missing and not invalid,
            "missing": missing,
            "invalid": invalid,
            "error": "" if not missing and not invalid else "recovery range incomplete",
        }

    def _import_block_into_chain_sim_db(self, blk: Dict[str, Any]) -> bool:
        """
        Import a block dict returned by chain_sim_ledger.get_block() into sqlite persistence.
        Minimal PR4.2: write blocks row + tx rows + commit header roots.
        """
        if not isinstance(blk, dict):
            return False

        h = int(blk.get("height") or 0)
        if h <= 0:
            return False

        created_at_ms = int(blk.get("created_at_ms") or 0) or int(_now_ms())

        header = blk.get("header") or {}
        if not isinstance(header, dict):
            header = {}

        # roots can be top-level or in header; normalize for persist_commit_block()
        state_root = blk.get("state_root") or header.get("state_root")
        txs_root = blk.get("txs_root") or header.get("txs_root")

        header_patch = dict(header)
        if state_root:
            header_patch["state_root"] = str(state_root)
        if txs_root:
            header_patch["txs_root"] = str(txs_root)

        txs = blk.get("txs") or []
        if not isinstance(txs, list):
            txs = []

        try:
            from backend.modules.chain_sim.chain_sim_ledger import (
                persist_begin_block,
                persist_tx_row,
                persist_commit_block,
            )
        except Exception:
            return False

        # Ensure the block shell exists BEFORE inserting tx rows (foreign key)
        try:
            persist_begin_block(h, created_at_ms, header=header_patch)
        except Exception:
            pass

        # Insert tx rows
        for i, t in enumerate(txs):
            if not isinstance(t, dict):
                continue

            try:
                tx_id = str(t.get("tx_id") or "")
                tx_hash = str(t.get("tx_hash") or "")
                from_addr = str(t.get("from_addr") or "")
                nonce = int(t.get("nonce") or 0)
                tx_type = str(t.get("tx_type") or "")
                payload = t.get("payload") or {}
                if not isinstance(payload, dict):
                    payload = {}
                applied = bool(t.get("applied", True))
                result = t.get("result") or {}
                if not isinstance(result, dict):
                    result = {}
                fee = t.get("fee")
                fee = fee if isinstance(fee, dict) else None

                # tx_index: prefer provided value, else fall back to list index
                tx_index = int(t.get("tx_index") or i)

                if not tx_id or not tx_hash or not from_addr or not tx_type:
                    continue

                persist_tx_row(
                    {
                        "tx_id": tx_id,
                        "tx_hash": tx_hash,
                        "block_height": h,
                        "tx_index": tx_index,
                        "from_addr": from_addr,
                        "nonce": nonce,
                        "tx_type": tx_type,
                        "payload": payload,
                        "applied": applied,
                        "result": result,
                        "fee": fee,
                    }
                )
            except Exception:
                continue

        # Commit header + roots (also patches tx result_json roots via persist_commit_block())
        try:
            persist_commit_block(h, header_patch)
        except Exception:
            # even if this fails, we may still have block shell + tx rows
            pass

        return True


    def _peers_snapshot(self) -> List[Dict[str, Any]]:
        """
        Peers from peer_store. Returns list of dicts with at least base_url.
        """
        try:
            from backend.modules.p2p.peer_store import load_peers_from_env, list_peers
            load_peers_from_env()
            out: List[Dict[str, Any]] = []
            for p in list_peers():
                base = (getattr(p, "base_url", "") or "").strip()
                if not base:
                    continue
                # best-effort fields (may not exist on p)
                out.append(
                    {
                        "base_url": base,
                        "node_id": getattr(p, "node_id", None),
                        "val_id": getattr(p, "val_id", None),
                        "hello_ok": bool(getattr(p, "hello_ok", False)),
                        "relay_url": getattr(p, "relay_url", None),
                    }
                )
            return out
        except Exception:
            return []

    async def _sync_blocks_range(self, from_h: int, to_h: int, *, tip_qc: Optional[QC] = None) -> Dict[str, Any]:
        """
        PR4.2/PR4.4: for each missing height in [from_h..to_h], fetch via /api/p2p/block_req
        with per-peer lane backoff + height-based retry schedule + peer rotation.
        """
        if request_block is None:
            return {"complete": False, "missing": [], "imported": [], "error": "block transport unavailable"}

        a = int(from_h or 0)
        b = int(to_h or 0)
        if a <= 0 or b <= 0 or a > b:
            return {"complete": False, "missing": [], "imported": [], "error": "bad height range"}
        if b - a + 1 > self._max_recovery_blocks:
            return {
                "complete": False, "missing": [], "imported": [],
                "error": "recovery height range exceeds limit",
            }

        # cheap in-flight guard (avoid multiple concurrent replays)
        with self._lock:
            if self._syncing_blocks:
                return {"complete": False, "missing": list(range(a, b + 1)), "imported": [], "error": "block recovery already running"}
            self._syncing_blocks = True

        imported_any = False
        imported_heights: list[int] = []
        lane = "BLOCK_REQ"

        try:
            for h in range(a, b + 1):
                local_block = self._read_local_block(h)
                local_error = (
                    self._verify_recovery_block(
                        local_block,
                        height=h,
                        tip_qc=tip_qc if h == b else None,
                    )
                    if local_block is not None else "missing"
                )
                if local_block is not None and local_error is None:
                    # if we already have it, clear any height-fail counter
                    try:
                        self._sync_height_fails.pop(h, None)
                    except Exception:
                        pass
                    continue

                # height-based pause (prevents tight loops when nobody has the block yet)
                attempts = 0
                try:
                    attempts = int(self._sync_height_fails.get(h, 0))
                except Exception:
                    attempts = 0

                if attempts > 0:
                    sleep_ms = min(150 * (2 ** min(attempts, 6)), 2500)
                    await asyncio.sleep(float(sleep_ms) / 1000.0)

                peers = self._peers_snapshot()
                if not peers:
                    # no peers yet; count as a failed height attempt
                    self._sync_height_fails[h] = attempts + 1
                    continue

                random.shuffle(peers)

                filled = False

                for peer in peers:
                    if not isinstance(peer, dict):
                        continue
                    base_url = (peer.get("base_url") or "").strip()
                    if not base_url:
                        continue

                    peer_key = (peer.get("val_id") or peer.get("node_id") or base_url).strip()
                    if not peer_key:
                        continue

                    # per-peer lane gate (rate/backoff/inflight)
                    try:
                        if not self._sync_policy.allow(peer_key, lane):
                            continue
                        self._sync_policy.on_attempt(peer_key, lane)
                    except Exception:
                        # if policy misbehaves, fail open but still attempt once
                        pass

                    try:
                        r = await request_block(
                            chain_id=self.chain_id,
                            from_node_id=self.node_id,
                            from_val_id=self.self_val_id,
                            height=h,
                            want="block",
                            peer_base_url=base_url,  # IMPORTANT: peer-specific
                        )
                    except Exception as e:
                        try:
                            self._sync_policy.on_failure(peer_key, lane, err=repr(e))
                        except Exception:
                            pass
                        continue

                    # normalize response shape
                    ok = bool(isinstance(r, dict) and (r.get("ok") is True))
                    blk = r.get("block") if isinstance(r, dict) else None

                    if not ok or not isinstance(blk, dict):
                        try:
                            self._sync_policy.on_failure(peer_key, lane, err=f"not ok: {r}")
                        except Exception:
                            pass
                        continue

                    if int(blk.get("height") or 0) != int(h):
                        try:
                            self._sync_policy.on_failure(peer_key, lane, err="height mismatch")
                        except Exception:
                            pass
                        continue

                    block_error = self._verify_recovery_block(
                        blk,
                        height=h,
                        tip_qc=tip_qc if h == b else None,
                    )
                    if block_error:
                        try:
                            self._sync_policy.on_failure(peer_key, lane, err=block_error)
                        except Exception:
                            pass
                        continue

                    # import
                    imported = False
                    try:
                        imported = bool(self._import_block_into_chain_sim_db(blk))
                    except Exception as e:
                        imported = False

                    if imported:
                        imported_any = True
                        imported_heights.append(h)
                        filled = True
                        try:
                            self._sync_policy.on_success(peer_key, lane)
                        except Exception:
                            pass
                        break
                    else:
                        try:
                            self._sync_policy.on_failure(peer_key, lane, err="import failed")
                        except Exception:
                            pass
                        continue

                if filled:
                    try:
                        self._sync_height_fails.pop(h, None)
                    except Exception:
                        pass
                else:
                    self._sync_height_fails[h] = attempts + 1

            # refresh in-memory state once per batch
            if imported_any:
                try:
                    from backend.modules.chain_sim.chain_sim_ledger import replay_state_from_db
                    replay_state_from_db()
                except Exception:
                    pass

            checked = self._local_recovery_range_status(a, b, tip_qc=tip_qc)
            return {
                **checked,
                "imported": imported_heights,
            }

        finally:
            with self._lock:
                self._syncing_blocks = False

    def _validate_sync_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a peer tip without mutating consensus or persistent state."""
        try:
            peer_fh = int(payload.get("finalized_height") or 0)
        except Exception:
            peer_fh = 0

        if peer_fh <= 0:
            return {"ok": False, "error": "no peer finalized_height"}

        qc_d = payload.get("last_qc")
        if not isinstance(qc_d, dict):
            return {"ok": False, "error": "no last_qc"}

        try:
            qc = QC(**qc_d)  # type: ignore[arg-type]
        except Exception:
            return {"ok": False, "error": "bad qc"}

        # ✅ linkage: finalized_height must match qc.height (otherwise reject)
        try:
            qc_h = int(getattr(qc, "height", 0) or 0)
        except Exception:
            qc_h = 0
        if qc_h != int(peer_fh):
            return {"ok": False, "error": "sync_resp invalid: finalized_height != last_qc.height"}

        # Snapshot local state.  A behind view cannot change state and is not a
        # recovery candidate, so it is ignored before expensive certificate
        # verification just as the legacy sync path did.
        with self._lock:
            local_fh = int(self._finalized_height)
            local_last = self._last_qc

        # ✅ If peer is behind us, ignore (do NOT treat as an error).
        if int(peer_fh) < int(local_fh):
            return {
                "ok": True,
                "behind": True,
                "peer_fh": peer_fh,
                "local_fh": local_fh,
                "qc": qc,
            }

        # Validate the certificate independently of local monotonic state.  A
        # same-height different finalized block is not merely malformed input:
        # it is a safety conflict that must be durably halted and surfaced.
        err = _validate_qc_structural_or_error(qc, vset=self.vset, last_qc=None, expect_height=peer_fh)
        if err:
            return {"ok": False, "error": err}
        finality_error = self._qc_finality_error(qc)
        if finality_error:
            return {"ok": False, "error": finality_error}

        local_block_id = str(getattr(local_last, "block_id", "") or "") if local_last else ""
        conflict = bool(
            local_last is not None
            and int(peer_fh) == int(local_fh)
            and str(qc.block_id) != local_block_id
        )
        return {
            "ok": True,
            "behind": False,
            "peer_fh": peer_fh,
            "local_fh": local_fh,
            "local_block_id": local_block_id,
            "conflict_with_local": conflict,
            "qc": qc,
        }

    def _apply_validated_sync_tip(self, validated: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Commit a previously validated tip only after its ledger range exists."""
        qc = validated.get("qc")
        if not isinstance(qc, QC):
            return {"ok": False, "error": "validated sync tip missing qc"}
        peer_fh = int(validated.get("peer_fh") or 0)
        if self._partition_recovery_halted():
            return {"ok": False, "error": "partition recovery safety halt"}

        with self._lock:
            local_fh = int(self._finalized_height)
        if peer_fh <= local_fh:
            return {"ok": True, "applied": False, "finalized_height": local_fh, "old_fh": local_fh}

        material = self._local_recovery_range_status(local_fh + 1, peer_fh, tip_qc=qc)
        if not material.get("complete"):
            return {
                "ok": True,
                "applied": False,
                "recovery_required": True,
                "finalized_height": local_fh,
                "old_fh": local_fh,
                "missing": material.get("missing", []),
                "invalid": material.get("invalid", []),
            }

        old_fh = local_fh

        with self._lock:
            # Recheck after block acquisition in case live consensus advanced.
            old_fh = int(self._finalized_height)
            if peer_fh <= old_fh:
                return {"ok": True, "applied": False, "finalized_height": old_fh, "old_fh": old_fh}
            err2 = self._qc_monotonicity_error_locked(qc)
            if err2:
                return {"ok": False, "error": err2}
            self._finalized_height = int(peer_fh)
            if self._last_qc is None or _is_qc_strictly_newer(qc, self._last_qc):
                self._last_qc = qc
            self._retain_finality_qc_locked(qc)
            self._cur_height = int(self._finalized_height) + 1
            self._cur_round = 0
            self._round_started_ms = _now_ms()

        try:
            save_state(
                int(self._finalized_height),
                self._last_qc.model_dump() if self._last_qc else None,
                round=int(payload.get("round") or 0),
            )
        except Exception:
            pass

        # The exact blocks already exist.  This patches only the trusted tip
        # metadata and never fabricates missing intermediate shell blocks.
        try:
            self._persist_finalized_block_shell(
                height=int(peer_fh),
                block_id=str(qc.block_id),
                qc=qc,
                created_at_ms=int(qc.ts_ms or _now_ms()),
            )
        except Exception:
            pass

        self._set_partition_recovery_phase(
            PHASE_HEALTHY,
            reason="trusted_tip_materialized_and_applied",
            local_finalized_height=int(peer_fh),
            valid_view_count=int(validated.get("valid_view_count") or 1),
        )

        return {
            "ok": True,
            "applied": True,
            "finalized_height": int(self._finalized_height),
            "old_fh": int(old_fh),
        }

    def handle_sync_resp(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pushed sync data without advancing ahead of ledger material."""
        validated = self._validate_sync_payload(payload)
        if not validated.get("ok"):
            return validated
        if validated.get("behind"):
            local_fh = int(validated.get("local_fh") or 0)
            return {"ok": True, "applied": False, "finalized_height": local_fh, "old_fh": local_fh}

        qc = validated["qc"]
        classification = classify_validated_views(
            [{"height": int(qc.height), "round": int(qc.round), "block_id": str(qc.block_id)}],
            local_height=int(validated.get("local_fh") or 0),
            local_block_id=str(validated.get("local_block_id") or ""),
        )
        if classification["phase"] == PHASE_SAFETY_HALT:
            state = self._set_partition_recovery_phase(
                PHASE_SAFETY_HALT,
                reason=str(classification["reason"]),
                local_finalized_height=int(validated.get("local_fh") or 0),
                target_finalized_height=int(qc.height),
                target_block_id=str(qc.block_id),
                target_round=int(qc.round),
                valid_view_count=1,
                conflict_digest=str(classification.get("conflict_digest") or ""),
                conflicting_heights=classification.get("conflicting_heights", []),
                last_error="conflicting trusted finalized block at local height",
            )
            return {"ok": False, "error": "conflicting trusted finality view", "halt_id": state.get("halt_id")}

        local_fh = int(validated.get("local_fh") or 0)
        if int(qc.height) <= local_fh:
            return {"ok": True, "applied": False, "finalized_height": local_fh, "old_fh": local_fh}
        material = self._local_recovery_range_status(local_fh + 1, int(qc.height), tip_qc=qc)
        if not material.get("complete"):
            self._set_partition_recovery_phase(
                PHASE_BLOCK_CATCHUP,
                reason="trusted_tip_waiting_for_ledger_material",
                local_finalized_height=local_fh,
                target_finalized_height=int(qc.height),
                target_block_id=str(qc.block_id),
                target_round=int(qc.round),
                valid_view_count=1,
                missing_from_height=local_fh + 1,
                missing_to_height=int(qc.height),
                last_error=str(material.get("error") or "ledger material missing"),
            )
            return {
                "ok": True,
                "applied": False,
                "recovery_required": True,
                "finalized_height": local_fh,
                "old_fh": local_fh,
            }
        return self._apply_validated_sync_tip(validated, payload)

    async def _sync_once(self) -> None:
        """
        Assess all trusted peer views, materialize any missing ledger range, and
        only then advance the persisted finalized tip.  Conflicting trusted
        finality at one height enters a sticky safety halt.
        """
        if request_sync_one is None:
            return
        if not self.self_val_id or not self.vset.is_member(self.self_val_id):
            return

        peers = self._peers_snapshot()
        if not peers:
            with self._lock:
                local_fh = int(self._finalized_height)
            self._set_partition_recovery_phase(
                PHASE_PARTITION_SUSPECTED,
                reason="no_configured_peers_available",
                local_finalized_height=local_fh,
                valid_view_count=0,
                last_error="no peers available for finality assessment",
            )
            return

        random.shuffle(peers)
        lane = "SYNC_REQ"

        payloads: list[tuple[Dict[str, Any], str]] = []
        with self._lock:
            local_fh = int(self._finalized_height)

        for peer in peers:
            if not isinstance(peer, dict):
                continue
            base_url = (peer.get("base_url") or "").strip()
            if not base_url:
                continue

            peer_key = (peer.get("val_id") or peer.get("node_id") or base_url).strip()
            if not peer_key:
                continue

            # per-peer lane gate
            try:
                if not self._sync_policy.allow(peer_key, lane):
                    continue
                self._sync_policy.on_attempt(peer_key, lane)
            except Exception:
                pass

            try:
                if ensure_peer_hello is not None and not bool(peer.get("hello_ok")):
                    await ensure_peer_hello(
                        chain_id=self.chain_id,
                        from_node_id=self.node_id,
                        from_val_id=self.self_val_id,
                        peer_base_url=base_url,
                        finalized_height=local_fh,
                    )
                r = await request_sync_one(
                    chain_id=self.chain_id,
                    from_node_id=self.node_id,
                    from_val_id=self.self_val_id,
                    peer_base_url=base_url,
                )
            except Exception as e:
                try:
                    self._sync_policy.on_failure(peer_key, lane, err=repr(e))
                except Exception:
                    pass
                continue

            if not isinstance(r, dict) or r.get("ok") is not True or not isinstance(r.get("payload"), dict):
                try:
                    self._sync_policy.on_failure(peer_key, lane, err=f"not ok: {r}")
                except Exception:
                    pass
                continue

            try:
                self._sync_policy.on_success(peer_key, lane)
            except Exception:
                pass

            payloads.append((r["payload"], peer_digest(peer_key)))

        if not payloads:
            with self._lock:
                local_fh = int(self._finalized_height)
            self._set_partition_recovery_phase(
                PHASE_PARTITION_SUSPECTED,
                reason="trusted_peers_unreachable_or_invalid",
                local_finalized_height=local_fh,
                valid_view_count=0,
                last_error="no trusted peer sync response accepted",
            )
            return

        with self._lock:
            local_fh = int(self._finalized_height)
            local_block_id = str(getattr(self._last_qc, "block_id", "") or "") if self._last_qc else ""

        validated_payloads: list[tuple[Dict[str, Any], Dict[str, Any], str]] = []
        views: list[Dict[str, Any]] = []
        for index, (payload, source_digest) in enumerate(payloads):
            validated = self._validate_sync_payload(payload)
            if not validated.get("ok") or validated.get("behind"):
                continue
            qc = validated.get("qc")
            if not isinstance(qc, QC):
                continue
            validated_payloads.append((payload, validated, source_digest))
            views.append({
                "height": int(qc.height),
                "round": int(qc.round),
                "block_id": str(qc.block_id),
                "source_digest": source_digest,
                "payload_index": len(validated_payloads) - 1,
            })

        if not views:
            self._set_partition_recovery_phase(
                PHASE_PARTITION_SUSPECTED,
                reason="no_cryptographically_valid_peer_finality_view",
                local_finalized_height=local_fh,
                valid_view_count=0,
                last_error="peer responses did not yield a valid finality view",
            )
            return

        self._set_partition_recovery_phase(
            PHASE_REJOIN_ASSESSING,
            reason="trusted_peer_views_collected",
            local_finalized_height=local_fh,
            valid_view_count=len(views),
            last_error="",
        )
        classification = classify_validated_views(
            views,
            local_height=local_fh,
            local_block_id=local_block_id,
        )
        if classification["phase"] == PHASE_SAFETY_HALT:
            self._set_partition_recovery_phase(
                PHASE_SAFETY_HALT,
                reason=str(classification["reason"]),
                local_finalized_height=local_fh,
                valid_view_count=int(classification.get("valid_view_count") or 0),
                conflict_digest=str(classification.get("conflict_digest") or ""),
                conflicting_heights=classification.get("conflicting_heights", []),
                last_error="trusted peers reported conflicting finalized blocks",
            )
            return

        # Never auto-clear a safety halt merely because a later poll looks calm.
        if self._partition_recovery_halted():
            return

        candidate = classification.get("candidate")
        if not isinstance(candidate, dict):
            self._set_partition_recovery_phase(
                PHASE_HEALTHY,
                reason="trusted_peers_confirm_no_higher_finality",
                local_finalized_height=local_fh,
                valid_view_count=len(views),
            )
            return

        candidate_index = int(candidate.get("payload_index") or 0)
        if candidate_index < 0 or candidate_index >= len(validated_payloads):
            return
        payload, validated, source_digest = validated_payloads[candidate_index]
        qc = validated.get("qc")
        if not isinstance(qc, QC):
            return
        target_height = int(qc.height)
        gap = target_height - local_fh
        maximum_block_gap = max(1, int(os.getenv("CONSENSUS_PARTITION_BLOCK_CATCHUP_MAX", "512") or "512"))
        if gap > maximum_block_gap:
            self._set_partition_recovery_phase(
                PHASE_SNAPSHOT_REQUIRED,
                reason="partition_gap_exceeds_bounded_block_catchup",
                local_finalized_height=local_fh,
                target_finalized_height=target_height,
                target_block_id=str(qc.block_id),
                target_round=int(qc.round),
                source_peer_digest=source_digest,
                valid_view_count=len(views),
                missing_from_height=local_fh + 1,
                missing_to_height=target_height,
                last_error="verified snapshot synchronization required before finality can advance",
            )
            return

        prior = self._partition_recovery_status()
        attempts = int(prior.get("recovery_attempts") or 0) + 1
        self._set_partition_recovery_phase(
            PHASE_BLOCK_CATCHUP,
            reason="materializing_trusted_finality_range",
            local_finalized_height=local_fh,
            target_finalized_height=target_height,
            target_block_id=str(qc.block_id),
            target_round=int(qc.round),
            source_peer_digest=source_digest,
            valid_view_count=len(views),
            missing_from_height=local_fh + 1,
            missing_to_height=target_height,
            recovery_attempts=attempts,
            last_error="",
        )
        recovered = await self._sync_blocks_range(local_fh + 1, target_height, tip_qc=qc)
        if not recovered.get("complete"):
            missing = recovered.get("missing") if isinstance(recovered.get("missing"), list) else []
            invalid = recovered.get("invalid") if isinstance(recovered.get("invalid"), list) else []
            self._set_partition_recovery_phase(
                PHASE_BLOCK_CATCHUP,
                reason="trusted_finality_range_incomplete",
                local_finalized_height=local_fh,
                target_finalized_height=target_height,
                target_block_id=str(qc.block_id),
                target_round=int(qc.round),
                source_peer_digest=source_digest,
                valid_view_count=len(views),
                missing_from_height=min(missing) if missing else local_fh + 1,
                missing_to_height=max(missing) if missing else target_height,
                recovery_attempts=attempts,
                last_error=str(recovered.get("error") or invalid or "ledger range incomplete")[:500],
            )
            return

        validated["valid_view_count"] = len(views)
        self._apply_validated_sync_tip(validated, payload)


    def _import_block_into_db(
        self,
        blk: Dict[str, Any],
        *,
        persist_begin_block: Any,
        persist_commit_block: Any,
        persist_tx_row: Any,
        compute_tx_identity: Any,
    ) -> bool:
        """
        Store a peer-supplied block dict into sqlite using chain_sim_ledger persistence helpers.
        Expected shape (best-effort):
          blk = {"height":..., "created_at_ms":..., "header":..., "txs":[...], "txs_root":..., "state_root":...}
        """
        try:
            h = int(blk.get("height") or 0)
            if h <= 0:
                return False

            created_at_ms = int(blk.get("created_at_ms") or _now_ms())
            header = blk.get("header") or {}
            if not isinstance(header, dict):
                header = {}

            txs = blk.get("txs") or []
            if not isinstance(txs, list):
                txs = []

            # begin shell block row
            persist_begin_block(h, created_at_ms, header=header)

            # persist tx rows
            for idx, tx in enumerate(txs):
                if not isinstance(tx, dict):
                    continue

                from_addr = str(tx.get("from_addr") or "")
                nonce = int(tx.get("nonce") or 0)
                tx_type = str(tx.get("tx_type") or "")
                payload = tx.get("payload") or {}
                if not isinstance(payload, dict):
                    payload = {}

                # ensure tx_hash/tx_id stable with local identity rules
                tx_id = tx.get("tx_id")
                tx_hash = tx.get("tx_hash")
                if not isinstance(tx_hash, str) or not tx_hash:
                    tx_id2, tx_hash2 = compute_tx_identity(from_addr, nonce, tx_type, payload)
                    tx_hash = tx_hash2
                    if not isinstance(tx_id, str) or not tx_id:
                        tx_id = tx_id2
                elif not isinstance(tx_id, str) or not tx_id:
                    tx_id2, _ = compute_tx_identity(from_addr, nonce, tx_type, payload)
                    tx_id = tx_id2

                result = tx.get("result") or {}
                if not isinstance(result, dict):
                    result = {}

                fee = tx.get("fee")
                fee = fee if isinstance(fee, dict) else None

                persist_tx_row(
                    {
                        "tx_id": str(tx_id),
                        "tx_hash": str(tx_hash),
                        "block_height": h,
                        "tx_index": int(tx.get("tx_index") or idx),
                        "from_addr": from_addr,
                        "nonce": nonce,
                        "tx_type": tx_type,
                        "payload": payload,
                        "applied": bool(tx.get("applied", True)),
                        "result": result,
                        "fee": fee,
                    }
                )

            # commit header roots
            state_root = blk.get("state_root") or header.get("state_root") or ""
            txs_root = blk.get("txs_root") or header.get("txs_root") or ""

            patch: Dict[str, Any] = {}
            if isinstance(state_root, str) and state_root:
                patch["state_root"] = state_root
            if isinstance(txs_root, str) and txs_root:
                patch["txs_root"] = txs_root

            persist_commit_block(h, patch if patch else dict(header))

            return True
        except Exception:
            return False

    # -------------------------
    # helpers
    # -------------------------

    def _proposal_wins_over(a: Proposal, b: Proposal) -> bool:
        # True if a beats b
        try:
            return str(_proposal_fingerprint(a)) < str(_proposal_fingerprint(b))
        except Exception:
            # safest: never “win” on error
            return False

    def _pctl(vals: list[float], p: float) -> float:
        if not vals:
            return 0.0
        v = sorted(vals)
        if p <= 0:
            return float(v[0])
        if p >= 100:
            return float(v[-1])
        # nearest-rank
        k = int(round((p / 100.0) * (len(v) - 1)))
        k = max(0, min(len(v) - 1, k))
        return float(v[k])

    def _record_round_hint(self, *, height: int, round: int) -> None:
        h = int(height)
        r = int(round)
        if h <= 0 or r < 0:
            return

        bumped = False
        with self._lock:
            prev = int(self._round_hint.get(h, -1))
            if r > prev:
                self._round_hint[h] = r
                bumped = True

        # IMPORTANT: if preferred round moved up for a (possibly future) height,
        # immediately drop cached lower-round traffic so it can’t later form QC.
        if bumped:
            self._prune_cached_below_round_for_height(height=h, min_round=r)

    def _preferred_round_for_height(self, *, height: int, fallback_round: int) -> int:
        h = int(height)
        fr = int(fallback_round)

        with self._lock:
            hint = int(self._round_hint.get(h, fr))
            curh = int(self._cur_height)
            curr = int(self._cur_round)

            pref = max(hint, fr)
            if curh == h:
                pref = max(pref, curr)

            # optional: if you ever treat last_qc as a “preference” at same height
            if self._last_qc is not None:
                try:
                    if int(self._last_qc.height) == h:
                        pref = max(pref, int(self._last_qc.round))
                except Exception:
                    pass

        return int(pref)

    def _maybe_apply_round_hint_current_height(self) -> None:
        with self._lock:
            h = int(self._cur_height)
            hint = int(self._round_hint.get(h, -1))
            if hint > int(self._cur_round):
                self._cur_round = hint
                self._round_started_ms = _now_ms()
                r = int(self._cur_round)
            else:
                return
        self._prune_for_height_round(height=h, round=r)

    def _maybe_fast_forward_round(self, *, height: int, round: int) -> None:
        """
        PR6 gate: if we observe traffic for a higher round at our current height,
        jump our local round forward so we converge (avoid spinning in lower rounds).
        """
        h = int(height)
        r = int(round)

        with self._lock:
            if int(self._cur_height) != h:
                return
            if int(self._cur_round) >= r:
                return

            # fast-forward local round + restart round timer
            self._cur_round = r
            self._round_started_ms = _now_ms()

        # prune old per-(h,r) caches outside lock
        self._prune_for_height_round(height=h, round=r)

    def _spawn_async(self, coro: Any) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        try:
            loop.create_task(coro)  # type: ignore[arg-type]
        except Exception:
            pass

    async def _maybe_send_vote(self, *, height: int, round: int, vote_type: VoteType, block_id: str) -> None:
        if not self.self_val_id or not self.vset.is_member(self.self_val_id):
            return
        if self._partition_recovery_halted():
            return
        if not self._protocol_upgrade_status(next_height=int(height)).get("consensus_allowed"):
            return

        h = int(height)
        r = int(round)
        bid = str(block_id)

        # ✅ PR6.2: don't vote below preferred round for this height
        with self._lock:
            pref = self._preferred_round_for_height_locked(height=h, fallback_round=r)
            if int(r) < int(pref):
                return

        with self._lock:
            if self._lock_block_id is not None and int(self._lock_height) == h:
                # PR6.1: round-aware self vote suppression (allow higher-round prevotes to enable unlock paths)
                if str(self._lock_block_id) != bid and int(r) <= int(self._lock_round):
                    return

        with self._lock:
            proposal = self._proposals.get((h, r))
        ledger_commitment = str(getattr(proposal, "ledger_commitment", "") or "")
        txs_root = str(getattr(proposal, "txs_root", "") or "")
        if self._finality_checkpoint is not None and (not ledger_commitment or not txs_root):
            return

        sent_key = (h, r, vote_type, bid, str(self.self_val_id))
        with self._lock:
            if sent_key in self._sent:
                return
            self._sent.add(sent_key)

        v = Vote(
            height=h,
            round=r,
            voter=str(self.self_val_id),
            vote_type=vote_type,
            block_id=bid,
            ts_ms=_now_ms(),
            ledger_commitment=ledger_commitment or None,
            txs_root=txs_root or None,
        )

        if vote_type == "PRECOMMIT" and self._finality_checkpoint is not None:
            if self._finality_private_key is None:
                # A validator configured in the trusted set must never cast an
                # uncertifiable precommit.  This deliberately halts its own
                # finality contribution instead of degrading assurance.
                return
            context = self._finality_certificate_context(
                height=h,
                round=r,
                block_id=bid,
                ledger_commitment=ledger_commitment,
                txs_root=txs_root,
            )
            v.finality_signature_base64 = base64.b64encode(
                self._finality_private_key.sign(vote_sign_bytes(context, self.self_val_id))
            ).decode("ascii")
            v.finality_validator_set_root = self._finality_checkpoint.validator_set_root
            v.finality_checkpoint_id = self._finality_checkpoint.checkpoint_id

        out = self.handle_vote(v)

        if vote_type == "PRECOMMIT":
            # Only lock if our PRECOMMIT was accepted by state machine.
            if isinstance(out, dict) and out.get("ok") is True and out.get("accepted") is True:
                with self._lock:
                    # ✅ Monotonic lock install: don’t let lower-height/round overwrite a newer lock.
                    if (
                        self._lock_block_id is None
                        or int(h) > int(self._lock_height)
                        or (int(h) == int(self._lock_height) and int(r) >= int(self._lock_round))
                    ):
                        self._lock_height = h
                        self._lock_round = r
                        self._lock_block_id = bid

        if _NET_OK and broadcast_vote is not None:
            try:
                payload = v.model_dump() if hasattr(v, "model_dump") else dict(v)  # type: ignore
                await broadcast_vote(
                    chain_id=self.chain_id,
                    from_node_id=self.node_id,
                    from_val_id=self.self_val_id,
                    payload=payload,
                )
            except Exception:
                pass

# -----------------------------------------------------------------------------
# module singleton
# -----------------------------------------------------------------------------

_ENGINE: Optional[ConsensusEngine] = None
_ENGINE_LOCK = threading.Lock()

def get_engine() -> ConsensusEngine:
    global _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is None:
            _ENGINE = ConsensusEngine()
        eng = _ENGINE

    # ✅ Ensure engine is actually running (safe: start() no-ops if no running loop)
    try:
        if _truthy("GLYPHCHAIN_CONSENSUS_ENABLE", True):
            eng.start()
    except Exception:
        pass

    return eng
