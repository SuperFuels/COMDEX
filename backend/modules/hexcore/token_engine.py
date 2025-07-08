import json
from pathlib import Path

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

STK_STORE = Path(__file__).parent / "stk_ledger.json"

class TokenEngine:
    def __init__(self):
        self.ledger = {}
        self._load()

    def _load(self):
        if STK_STORE.exists():
            with open(STK_STORE, "r") as f:
                self.ledger = json.load(f)
        else:
            self.ledger = {"aion": 0}
            self._save()

    def _save(self):
        with open(STK_STORE, "w") as f:
            json.dump(self.ledger, f, indent=2)

    def mint(self, user, amount):
        self.ledger[user] = self.ledger.get(user, 0) + amount
        self._save()

    def balance(self, user):
        return self.ledger.get(user, 0)

    def spend(self, user, amount):
        if self.ledger.get(user, 0) >= amount:
            self.ledger[user] -= amount
            self._save()
            return True
        return False
