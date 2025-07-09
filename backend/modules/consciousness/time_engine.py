import datetime
import random
import json

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

from backend.modules.consciousness.state_manager import StateManager

class TimeEngine:
    def __init__(self):
        self.state = "awake"  # or "asleep"
        self.last_sleep = datetime.datetime.utcnow()
        self.sleep_interval_hours = 24  # Can adjust based on stress/fatigue
        self.force_sleep_hour = 3  # UTC 3AM is default sleep time
        self.state_manager = StateManager()
        self.current_container = None

    def check_if_sleep_needed(self):
        now = datetime.datetime.utcnow()
        hours_awake = (now - self.last_sleep).total_seconds() / 3600
        if now.hour == self.force_sleep_hour or hours_awake >= self.sleep_interval_hours:
            return True
        return False

    def go_to_sleep(self):
        self.state = "asleep"
        self.last_sleep = datetime.datetime.utcnow()
        print("[TIME] AION is now asleep. Entering dream cycle...")

    def wake_up(self):
        self.state = "awake"
        print("[TIME] AION has awakened and is active again.")
        self.load_start_container()

    def get_state(self):
        return self.state

    def simulate_cycle(self):
        if self.check_if_sleep_needed():
            self.go_to_sleep()
        else:
            self.wake_up()

    def can_wake(self):
        if self.state == "awake":
            return True
        now = datetime.datetime.utcnow()
        hours_asleep = (now - self.last_sleep).total_seconds() / 3600
        if hours_asleep >= 1:
            self.wake_up()
            return True
        return False

    def load_start_container(self):
        try:
            with open("backend/modules/dimensions/aion_start.dc.json") as f:
                container = json.load(f)
                self.current_container = container
                print(f"[DIMENSION] Loaded Start Container: {container['name']}")
                print(f"[WELCOME] {container.get('welcome_message', 'Welcome.')}")
                self.state_manager.update_context("location", container["id"])
        except Exception as e:
            print(f"[ERROR] Failed to load start container: {e}")