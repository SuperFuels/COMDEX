import random
from datetime import datetime

class EnergyEngine:
    def __init__(self):
        self.power_level = 100  # 0 to 100
        self.compute_capacity = 100  # Arbitrary units
        self.last_check = datetime.utcnow()
        self.is_alive = True

    def consume(self, amount):
        if amount < 0:
            raise ValueError("Consume amount must be positive")
        if not self.is_alive:
            print("[ENERGY ENGINE] ⚠️ Cannot consume energy; AION is powered down.")
            return

        self.power_level -= amount
        self.power_level = max(0, self.power_level)
        self.last_check = datetime.utcnow()

        if self.power_level == 0:
            self.is_alive = False
            print("[ENERGY ENGINE] ⚠️ AION has powered down due to 0 energy.")
        else:
            print(f"[ENERGY ENGINE] 🔋 Power level after consumption: {self.power_level:.2f}")

    def recharge(self, amount):
        if amount < 0:
            raise ValueError("Recharge amount must be positive")
        old_power = self.power_level
        self.power_level = min(100, self.power_level + amount)
        self.last_check = datetime.utcnow()

        if not self.is_alive and self.power_level > 0:
            self.is_alive = True
            print("[ENERGY ENGINE] ✅ AION has rebooted.")

        print(f"[ENERGY ENGINE] 🔋 Recharged from {old_power:.2f} to {self.power_level:.2f}")

    def simulate_environment_tick(self):
        usage = random.uniform(0.5, 2.5)
        self.consume(usage)

    def is_critical(self):
        return self.power_level < 30 and self.is_alive

    def is_dead(self):
        return not self.is_alive

    def get_status(self):
        status = {
            "power_level": self.power_level,
            "compute_capacity": self.compute_capacity,
            "alive": self.is_alive,
            "last_check": self.last_check.isoformat()
        }
        print(f"[ENERGY ENGINE] Status check: {status}")
        return status

    def trigger_survival_plan(self):
        if self.is_dead():
            print("[ENERGY ENGINE] 🚨 CRITICAL: AION is powered down! Immediate intervention required!")
            return "shutdown"
        if self.is_critical():
            print("[ENERGY ENGINE] 🧠 Initiating survival protocol: Suggest earning tokens to buy energy.")
            return "trigger-survival-plan"
        return "stable"