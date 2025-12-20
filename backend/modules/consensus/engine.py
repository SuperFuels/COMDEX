# backend/modules/consensus/engine.py
from __future__ import annotations
import hashlib
import json
import asyncio
import os
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import random
from backend.modules.consensus.sync_policy import SyncPolicy
from backend.modules.p2p.peer_store import load_peers_from_env, list_peers
from .store import load_state, save_state
from .types import Proposal, QC, Vote, VoteType
from .validator_set import ValidatorSet

# Optional networking layer (PR2). If missing, engine still runs but won't broadcast.
_NET_OK = True
_NET_ERR = ""
try:
    from .net import (
        broadcast_proposal,
        broadcast_vote,
        request_sync_one,
        request_block,
        request_blocks,
    ) # type: ignore
except Exception as e:  # pragma: no cover
    _NET_OK = False
    _NET_ERR = str(e)
    broadcast_proposal = None  # type: ignore
    broadcast_vote = None  # type: ignore
    request_sync_one = None  # type: ignore
    request_block = None  # type: ignore
    request_blocks = None  # type: ignore


def _stable_json_bytes(x: Any) -> bytes:
    try:
        return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except Exception:
        return repr(x).encode("utf-8")

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
    }
    return hashlib.sha256(_stable_json_bytes(canon)).hexdigest()


def _now_ms() -> float:
    return float(time.time() * 1000.0)

def _as_int(x: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        return int(x)
    except Exception:
        return default

def _canon_block_id(height: int, round: int, proposer: str) -> str:
    # MUST match tick() proposal creation format
    return f"h{int(height)}-r{int(round)}-P{str(proposer)}"

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
        self.self_val_id = (os.getenv("GLYPHCHAIN_SELF_VAL_ID", "") or "").strip()

        self.vset = ValidatorSet.from_env()

        # config knobs
        self._tick_ms = int(os.getenv("CONSENSUS_TICK_MS", "50") or "50")
        self._round_timeout_ms = int(os.getenv("CONSENSUS_ROUND_TIMEOUT_MS", "1500") or "1500")
        self._rebcast_s = float(os.getenv("CONSENSUS_PROPOSAL_REBCAST_S", "0.75") or "0.75")

        # PR4 sync knobs
        self._sync_every_ms = int(os.getenv("CONSENSUS_SYNC_EVERY_MS", "1500") or "1500")
        self._last_sync_ms: float = 0.0

        self._lock = threading.Lock()
        self._sync_policy = SyncPolicy()
        self._sync_height_fails: dict[int, int] = {}

        # proposal/vote storage
        self._proposals: Dict[Tuple[int, int], Proposal] = {}  # (h,r) -> Proposal
        self._votes: Dict[Tuple[int, int, VoteType, str], Set[str]] = {}  # (h,r,type,block_id) -> voters

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

        # round state should never start behind finalized_height
        self._cur_height: int = self._finalized_height + 1
        self._cur_round: int = int(ps.round or 0) if int(ps.finalized_height or 0) > 0 else 0
        self._round_started_ms: float = _now_ms()

        # background driver task
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_evt: Optional[asyncio.Event] = None

    # -------------------------
    # Introspection
    # -------------------------

    def status(self) -> Dict[str, Any]:
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

            # PR6.1: expose installed proposal identity (for gates / divergence debugging)
            prop = self._proposals.get((h, r))
            prop_fp = _proposal_fingerprint(prop) if prop is not None else None
            prop_bid = getattr(prop, "block_id", None) if prop is not None else None

        leader = self.leader_for(h, r)
        return {
            "ok": True,
            "chain_id": self.chain_id,
            "node_id": self.node_id,
            "self_val_id": self.self_val_id,
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
            "last_qc": (self._last_qc.model_dump() if self._last_qc else None),
        }

    def leader_for(self, height: int, round: int = 0) -> Optional[str]:
        ids = self.vset.ordered_ids()
        if not ids:
            return None
        idx = (int(height) - 1 + int(round)) % len(ids)
        return ids[idx]

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
                pass
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
            if int(self._lock_height) <= int(self._finalized_height):
                self._lock_height = 0
                self._lock_round = -1
                self._lock_block_id = None

            h = int(self._cur_height)
            r = int(self._cur_round)
        self._prune_for_height_round(height=h, round=r)

    # -------------------------
    # driver
    # -------------------------

    async def tick(self) -> None:
        if not self.self_val_id or not self.vset.is_member(self.self_val_id):
            return

        with self._lock:
            h = int(self._cur_height)
            r = int(self._cur_round)
            started = float(self._round_started_ms)

        # periodic sync (helps restart/missed windows catch up)
        now = _now_ms()
        do_sync = False
        with self._lock:
            if (now - float(self._last_sync_ms)) >= float(self._sync_every_ms):
                self._last_sync_ms = now
                do_sync = True
        if do_sync:
            self._spawn_async(self._sync_once())

        # timeout -> next round
        if (_now_ms() - started) >= float(self._round_timeout_ms):
            self._advance_round()
            return

        leader = self.leader_for(h, r)
        if not leader:
            return

        with self._lock:
            proposal = self._proposals.get((h, r))

        # if leader, create proposal if absent
        if proposal is None and leader == self.self_val_id:
            block_id = _canon_block_id(h, r, leader)

            # IMPORTANT: some Proposal models in this repo reject block=None
            # (and tick exceptions get swallowed), so default to {} and fallback defensively.
            try:
                p = Proposal(
                    height=h,
                    round=r,
                    proposer=leader,
                    block_id=block_id,
                    block={},          # <-- key fix
                    ts_ms=_now_ms(),
                )
            except Exception:
                # ultra-defensive fallback if Proposal is not a dataclass/pydantic mismatch
                payload = {
                    "height": h,
                    "round": r,
                    "proposer": leader,
                    "block_id": block_id,
                    "block": {},
                    "ts_ms": _now_ms(),
                }
                p = Proposal(**payload)  # type: ignore

            self.handle_proposal(p)
            proposal = p

        with self._lock:
            locked_h = int(self._lock_height)
            locked_r = int(self._lock_round)
            locked_bid = self._lock_block_id

        # ✅ If we’re locked at this height, only force-vote the locked block in the SAME round.
        # Once the round advances, we must vote the (h,r) proposal’s canonical block_id or abstain,
        # otherwise our own votes become non-canonical and the cluster deadlocks.
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

    # -------------------------
    # inbound handlers
    # -------------------------

    def handle_proposal(self, p: Proposal) -> Dict[str, Any]:
        h = _as_int(getattr(p, "height", None), None)
        r = _as_int(getattr(p, "round", None), None)
        proposer = str(getattr(p, "proposer", "") or "").strip()
        block_id = str(getattr(p, "block_id", "") or "").strip()

        if h is None or h <= 0:
            return {"ok": False, "error": "height must be > 0"}
        if r is None or r < 0:
            return {"ok": False, "error": "round must be >= 0"}
        if not block_id or not proposer:
            return {"ok": False, "error": "block_id and proposer required"}

        exp = self.leader_for(h, r)
        if exp and proposer != exp:
            return {"ok": False, "error": f"bad proposer: expected {exp}, got {proposer}"}

        expected_bid = _canon_block_id(h, r, proposer)
        if block_id != expected_bid:
            return {"ok": False, "error": f"non-canonical block_id (got={block_id}, want={expected_bid})"}

        # ✅ PR6 (gate): if we're locked at this height, reject ANY conflicting proposal (even higher round).
        with self._lock:
            if (
                self._lock_block_id is not None
                and int(self._lock_height) == int(h)
                and str(block_id) != str(self._lock_block_id)
            ):
                return {"ok": False, "error": "locked on different block_id"}

        # ✅ PR6.1: store proposal deterministically (first-wins); duplicates must match fingerprint
        with self._lock:
            existing = self._proposals.get((int(h), int(r)))
            if existing is None:
                self._proposals[(int(h), int(r))] = p
            else:
                if _proposal_fingerprint(existing) != _proposal_fingerprint(p):
                    return {"ok": False, "error": "competing proposal at same (height,round)"}
                # else: identical duplicate, ok

        # schedule our prevote attempt (idempotent via _sent)
        self._spawn_async(self._maybe_send_vote(height=int(h), round=int(r), vote_type="PREVOTE", block_id=block_id))
        return {"ok": True, "accepted": True}

    def handle_vote(self, v: Vote) -> Dict[str, Any]:
        h = _as_int(getattr(v, "height", None), None)
        r = _as_int(getattr(v, "round", None), None)
        voter = str(getattr(v, "voter", "") or "").strip()
        vote_type = getattr(v, "vote_type", None)
        block_id = str(getattr(v, "block_id", "") or "").strip()

        if h is None or h <= 0:
            return {"ok": False, "error": "height must be > 0"}
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
        exp_bid = _canon_block_id(int(h), int(r), str(exp_leader))
        if block_id != exp_bid:
            return {"ok": False, "error": f"non-canonical block_id (got={block_id}, want={exp_bid})"}

        # ✅ Under lock: reject votes for a conflicting value if we don't even have a matching
        # accepted proposal for that (h,r). This matches “delayed/conflicting msgs” gating.
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
                self._evidence.append(proof)
                return {"ok": False, "error": "equivocation detected", "equivocation": True, "proof": proof}
            if prev_bid is None:
                self._seen_votes[ev_key] = str(block_id)

        key = (int(h), int(r), vote_type, str(block_id))
        now_ms = float(getattr(v, "ts_ms", 0.0) or 0.0) or _now_ms()

        with self._lock:
            # PR6.1: round-aware lock enforcement + relock on higher-round prevote quorum
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

            power = 0
            for vv in s:
                power += self.vset.power_of(vv)
            quorum_reached = power >= self.vset.quorum_power()

            # Unlock/relock trigger: higher-round PREVOTE quorum for a different value -> relock to it
            if vote_type == "PREVOTE" and quorum_reached:
                if locked_bid is not None and int(self._lock_height) == int(h) and str(block_id) != locked_bid:
                    if int(r) > locked_r:
                        self._lock_height = int(h)
                        self._lock_round = int(r)
                        self._lock_block_id = str(block_id)

            if vote_type == "PRECOMMIT" and quorum_reached:
                if int(h) > int(self._finalized_height):
                    qc_out = QC(
                        height=int(h),
                        round=int(r),
                        vote_type="PRECOMMIT",
                        block_id=str(block_id),
                        voters=sorted(list(s)),
                        ts_ms=now_ms,
                    )

                    # ✅ PR6.1: QC must be structurally valid (defense-in-depth)
                    err = _validate_qc_structural_or_error(qc=qc_out, vset=self.vset, last_qc=self._last_qc)
                    if err:
                        return {"ok": False, "error": f"qc invalid: {err}"}

                    # only after QC is valid do we finalize + advance last_qc
                    self._finalized_height = int(h)
                    finalized = True

                    if self._last_qc is None or _is_qc_strictly_newer(qc_out, self._last_qc):
                        self._last_qc = qc_out
                        persist = True
                    else:
                        persist = True

        # if PREVOTE quorum reached, push PRECOMMIT
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
        }

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
            persist_begin_block(h, cam, header={})
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

        # best-effort: refresh any in-memory views if your chain_sim uses them
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
            persist_begin_block(h, created_at_ms, header={})
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
                    }
                )
            return out
        except Exception:
            return []

    async def _sync_blocks_range(self, from_h: int, to_h: int) -> None:
        """
        PR4.2/PR4.4: for each missing height in [from_h..to_h], fetch via /api/p2p/block_req
        with per-peer lane backoff + height-based retry schedule + peer rotation.
        """
        if request_block is None:
            return

        a = int(from_h or 0)
        b = int(to_h or 0)
        if a <= 0 or b <= 0 or a > b:
            return

        # cheap in-flight guard (avoid multiple concurrent replays)
        with self._lock:
            if self._syncing_blocks:
                return
            self._syncing_blocks = True

        imported_any = False
        lane = "BLOCK_REQ"

        try:
            for h in range(a, b + 1):
                if self._have_block_local(h):
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

                    # import
                    imported = False
                    try:
                        imported = bool(self._import_block_into_chain_sim_db(blk))
                    except Exception as e:
                        imported = False

                    if imported:
                        imported_any = True
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

        finally:
            with self._lock:
                self._syncing_blocks = False

    def handle_sync_resp(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply a peer's reported finalized tip if it has a valid QC and is ahead of us.
        PR6.1: reject QC regressions/conflicts at same finalized height.
        """
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

        # ✅ PR6.1 linkage: finalized_height must match qc.height (otherwise reject)
        try:
            qc_h = int(getattr(qc, "height", 0) or 0)
        except Exception:
            qc_h = 0
        if qc_h != int(peer_fh):
            return {"ok": False, "error": "sync_resp invalid: finalized_height != last_qc.height"}

        with self._lock:
            local_fh = int(self._finalized_height)
            local_last = self._last_qc

        # If peer is behind us, ignore (do NOT treat as an error).
        if int(peer_fh) < int(local_fh):
            return {"ok": True, "applied": False, "finalized_height": int(local_fh), "old_fh": int(local_fh)}

        # If peer claims SAME finalized height, QC must not regress/conflict.
        if int(peer_fh) == int(local_fh):
            err = _validate_qc_structural_or_error(qc, vset=self.vset, last_qc=local_last, expect_height=peer_fh)
            if err:
                return {"ok": False, "error": err}
            return {"ok": True, "applied": False, "finalized_height": int(local_fh), "old_fh": int(local_fh)}

        # Peer is ahead: QC must be structurally valid, and must not conflict with our last_qc ordering.
        err = _validate_qc_structural_or_error(qc, vset=self.vset, last_qc=local_last, expect_height=peer_fh)
        if err:
            return {"ok": False, "error": err}

        with self._lock:
            old_fh = int(self._finalized_height)

            self._finalized_height = int(peer_fh)
            self._last_qc = qc
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

        try:
            self._persist_finalized_shell_range(
                from_height=int(old_fh) + 1,
                to_height=int(peer_fh),
                tip_block_id=str(qc.block_id),
                tip_qc=qc,
                tip_created_at_ms=int(qc.ts_ms or _now_ms()),
            )
        except Exception:
            pass

        return {"ok": True, "applied": True, "finalized_height": int(self._finalized_height), "old_fh": int(old_fh)}

    def _persist_finalized_shell_range(
        self,
        *,
        from_height: int,
        to_height: int,
        tip_block_id: str,
        tip_qc: Optional[QC],
        tip_created_at_ms: int,
    ) -> None:
        a = int(from_height or 0)
        b = int(to_height or 0)
        if a <= 0 or b <= 0 or a > b:
            return

        for h in range(a, b + 1):
            if self._have_block_local(h):
                continue
            # for intermediate heights we only need a minimal shell; for tip, include qc
            if h == b:
                self._persist_finalized_block_shell(
                    height=h,
                    block_id=str(tip_block_id),
                    qc=tip_qc,
                    created_at_ms=int(tip_created_at_ms),
                )
            else:
                self._persist_finalized_block_shell(
                    height=h,
                    block_id=f"h{h}-shell",
                    qc=None,
                    created_at_ms=int(_now_ms()),
                )

    async def _sync_once(self) -> None:
        """
        Policy-backed SYNC_REQ polling:
          - peer rotation
          - per-peer lane backoff/rate via SyncPolicy
          - stop when an applied higher finalized tip is found
          - then fill blocks ONLY via _sync_blocks_range (policy-backed path)
        """
        if request_sync_one is None:
            return
        if not self.self_val_id or not self.vset.is_member(self.self_val_id):
            return

        peers = self._peers_snapshot()
        if not peers:
            return

        random.shuffle(peers)
        lane = "SYNC_REQ"

        payloads: list[Dict[str, Any]] = []

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

            payloads.append(r["payload"])

        if not payloads:
            return

        payloads.sort(key=lambda p: int(p.get("finalized_height") or 0), reverse=True)

        for p in payloads:
            out = self.handle_sync_resp(p)
            if isinstance(out, dict) and out.get("ok") and out.get("applied"):
                new_fh = int(out.get("finalized_height") or 0)
                old_fh = int(out.get("old_fh") or 0)
                if new_fh > 0 and new_fh > old_fh:
                    # ONE block-fill path: policy-backed BLOCK_REQ range fill
                    await self._sync_blocks_range(old_fh + 1, new_fh)
                return


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

        h = int(height)
        r = int(round)
        bid = str(block_id)

        with self._lock:
            if self._lock_block_id is not None and int(self._lock_height) == h:
                # PR6.1: round-aware self vote suppression (allow higher-round prevotes to enable unlock paths)
                if str(self._lock_block_id) != bid and int(r) <= int(self._lock_round):
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
        )

        out = self.handle_vote(v)

        if vote_type == "PRECOMMIT":
            # Only lock if our PRECOMMIT was accepted by state machine.
            if isinstance(out, dict) and out.get("ok") is True:
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
        return _ENGINE