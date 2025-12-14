# backend/modules/chain_sim/dev_ledger_store.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from .tx_models import TxRecord, Block

@dataclass
class DevLedgerStore:
    blocks: List[Block] = field(default_factory=list)
    tx_by_id: Dict[str, TxRecord] = field(default_factory=dict)
    tx_ids_by_address: Dict[str, List[str]] = field(default_factory=dict)

    def reset(self) -> None:
        self.blocks.clear()
        self.tx_by_id.clear()
        self.tx_ids_by_address.clear()

    def next_height(self) -> int:
        return len(self.blocks) + 1

    def add_tx(self, tx: TxRecord) -> None:
        self.tx_by_id[tx.tx_id] = tx

        # address index (simple: from + any explicit to in payload)
        self.tx_ids_by_address.setdefault(tx.envelope.from_addr, []).append(tx.tx_id)

        to_addr = None
        if isinstance(tx.envelope.payload, dict):
            to_addr = tx.envelope.payload.get("to_addr") or tx.envelope.payload.get("recipient")
        if isinstance(to_addr, str) and to_addr:
            self.tx_ids_by_address.setdefault(to_addr, []).append(tx.tx_id)

    def add_block(self, block: Block) -> None:
        self.blocks.append(block)

    def get_block(self, height: int) -> Optional[Block]:
        if height <= 0 or height > len(self.blocks):
            return None
        return self.blocks[height - 1]

    def list_blocks(self, limit: int = 50) -> List[Block]:
        return list(reversed(self.blocks[-limit:]))

    def get_tx(self, tx_id: str) -> Optional[TxRecord]:
        return self.tx_by_id.get(tx_id)

    def list_txs_for_address(self, address: str, limit: int = 50) -> List[TxRecord]:
        ids = self.tx_ids_by_address.get(address, [])
        out = []
        for tx_id in reversed(ids[-limit:]):
            tx = self.tx_by_id.get(tx_id)
            if tx:
                out.append(tx)
        return out