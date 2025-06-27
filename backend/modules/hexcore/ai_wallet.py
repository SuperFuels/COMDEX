import json
from pathlib import Path

WALLET_FILE = Path(__file__).parent / "aion_wallet.json"

class AIWallet:
    def __init__(self):
        self.balances = {}
        self.load_wallet()

    def load_wallet(self):
        if WALLET_FILE.exists():
            with open(WALLET_FILE, "r") as f:
                self.balances = json.load(f)

    def save_wallet(self):
        with open(WALLET_FILE, "w") as f:
            json.dump(self.balances, f, indent=2)

    def earn(self, token, amount):
        self.balances[token] = self.balances.get(token, 0) + amount
        self.save_wallet()

    def spend(self, token, amount):
        if self.can_afford(token, amount):
            self.balances[token] -= amount
            self.save_wallet()
            return True
        return False

    def can_afford(self, token, amount):
        return self.balances.get(token, 0) >= amount

    def get_balance(self, token):
        return self.balances.get(token, 0)

    def get_all_balances(self):
        return self.balances
