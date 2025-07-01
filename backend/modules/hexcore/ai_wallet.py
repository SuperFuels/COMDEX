import json
from pathlib import Path
from typing import Dict

WALLET_FILE = Path(__file__).parent / "aion_wallet.json"

class AIWallet:
    def __init__(self):
        self.balances: Dict[str, float] = {}
        self.default_tokens = ["STK", "GLU", "GTC"]
        self.load_wallet()
        # Ensure default tokens exist with zero balance
        for token in self.default_tokens:
            self.balances.setdefault(token, 0.0)
        self.save_wallet()

    def load_wallet(self) -> None:
        if WALLET_FILE.exists():
            try:
                with open(WALLET_FILE, "r") as f:
                    self.balances = json.load(f)
            except json.JSONDecodeError:
                print("⚠️ Wallet file corrupt. Starting fresh.")
                self.balances = {}

    def save_wallet(self) -> None:
        with open(WALLET_FILE, "w") as f:
            json.dump(self.balances, f, indent=2)

    def earn(self, token: str, amount: float) -> None:
        self.balances[token] = self.balances.get(token, 0.0) + amount
        print(f"💰 Earned {amount} {token}. New balance: {self.balances[token]}")
        self.save_wallet()

    def spend(self, token: str, amount: float) -> bool:
        if self.can_afford(token, amount):
            self.balances[token] -= amount
            print(f"💸 Spent {amount} {token}. New balance: {self.balances[token]}")
            self.save_wallet()
            return True
        else:
            print(f"❌ Insufficient {token} balance to spend {amount}. Current balance: {self.balances.get(token, 0)}")
            return False

    def can_afford(self, token: str, amount: float) -> bool:
        return self.balances.get(token, 0.0) >= amount

    def get_balance(self, token: str) -> float:
        return self.balances.get(token, 0.0)

    def get_all_balances(self) -> Dict[str, float]:
        return self.balances

    def reset_wallet(self) -> None:
        self.balances = {token: 0.0 for token in self.default_tokens}
        print("🔄 Wallet reset to zero balances.")
        self.save_wallet()