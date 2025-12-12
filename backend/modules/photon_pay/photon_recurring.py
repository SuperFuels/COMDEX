# backend/modules/photon_pay/photon_recurring.py

from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any, List, Literal
import time
import uuid

DecimalLike = Decimal | str | float | int
Frequency = Literal["DAILY", "WEEKLY", "MONTHLY"]


def _D(x: DecimalLike) -> Decimal:
  if isinstance(x, Decimal):
    return x
  try:
    return Decimal(str(x))
  except (InvalidOperation, ValueError) as e:
    raise ValueError(f"invalid decimal: {x!r}") from e


@dataclass
class PhotonRecurringInstruction:
  """
  Dev-only recurring PHO payment ("direct debit" / standing order).

  NOT final chain API – just enough to:
    - create recurring instructions
    - see them in admin / wallet UIs
    - later hook a scheduler that actually triggers payments.

  Semantics:
    - from_account → to_account
    - amount_pho every `frequency`
    - next_due_ms is when the *next* run should fire
    - active = False once cancelled or exhausted
  """

  instr_id: str

  from_account: str
  to_account: str
  amount_pho: str

  memo: Optional[str]

  frequency: Frequency        # "DAILY" | "WEEKLY" | "MONTHLY"
  next_due_ms: int            # ms epoch of next intended run

  created_at_ms: int
  last_run_at_ms: Optional[int]
  total_runs: int

  max_runs: Optional[int]     # None = unlimited
  active: bool

  def to_dict(self) -> Dict[str, Any]:
    return asdict(self)


# ───────────────────────────────────────────────
# Dev-only in-memory store
# ───────────────────────────────────────────────

_DEV_RECURRING: List[PhotonRecurringInstruction] = []
_DEV_RECURRING_BY_ID: Dict[str, PhotonRecurringInstruction] = {}


def dev_add_recurring(instr: PhotonRecurringInstruction) -> None:
  _DEV_RECURRING.append(instr)
  _DEV_RECURRING_BY_ID[instr.instr_id] = instr


def dev_list_recurring() -> List[PhotonRecurringInstruction]:
  # Oldest → newest
  return list(_DEV_RECURRING)


def dev_get_recurring(instr_id: str) -> Optional[PhotonRecurringInstruction]:
  return _DEV_RECURRING_BY_ID.get(instr_id)


def dev_cancel_recurring(instr_id: str) -> bool:
  instr = _DEV_RECURRING_BY_ID.get(instr_id)
  if not instr:
    return False
  instr.active = False
  return True


# ───────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────

def _freq_to_ms(freq: Frequency) -> int:
  """
  Approximate durations – good enough for dev:
    DAILY   ≈ 24h
    WEEKLY  ≈ 7d
    MONTHLY ≈ 30d
  """
  day_ms = 24 * 60 * 60 * 1000
  if freq == "DAILY":
    return day_ms
  if freq == "WEEKLY":
    return 7 * day_ms
  # MONTHLY
  return 30 * day_ms


def new_recurring_instruction(
  *,
  from_account: str,
  to_account: str,
  amount_pho: str,
  frequency: Frequency,
  memo: Optional[str] = None,
  first_due_ms: Optional[int] = None,
  max_runs: Optional[int] = None,
) -> PhotonRecurringInstruction:
  """
  Construct a new dev recurring instruction.

  For now this does NOT schedule any actual payments – that's a separate
  "engine" step. It just records the mandate.
  """
  if not from_account:
    raise ValueError("from_account is required")
  if not to_account:
    raise ValueError("to_account is required")

  amt = _D(amount_pho)
  if amt <= 0:
    raise ValueError("amount_pho must be positive")

  now_ms = int(time.time() * 1000)
  if first_due_ms is None:
    first_due_ms = now_ms + _freq_to_ms(frequency)

  instr = PhotonRecurringInstruction(
    instr_id=f"rec_{uuid.uuid4().hex}",
    from_account=from_account,
    to_account=to_account,
    amount_pho=str(amt),
    memo=memo,
    frequency=frequency,
    next_due_ms=first_due_ms,
    created_at_ms=now_ms,
    last_run_at_ms=None,
    total_runs=0,
    max_runs=max_runs,
    active=True,
  )
  return instr