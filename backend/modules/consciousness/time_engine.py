import datetime
import random

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class TimeEngine:
    def __init__(self):
        self.state = "awake"  # or "asleep"
        self.last_sleep = datetime.datetime.utcnow()
        self.sleep_interval_hours = 24  # Can adjust based on stress/fatigue
        self.force_sleep_hour = 3  # UTC 3AM is default sleep time

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

    def get_state(self):
        return self.state

    def simulate_cycle(self):
        if self.check_if_sleep_needed():
            self.go_to_sleep()
        else:
            self.wake_up()

    def can_wake(self):
        """
        Returns True if AION is allowed to wake (i.e., not currently asleep),
        or if it's time to wake up according to sleep schedule.
        """
        if self.state == "awake":
            return True
        # If asleep, check if enough time has passed to wake
        now = datetime.datetime.utcnow()
        hours_asleep = (now - self.last_sleep).total_seconds() / 3600
        # Wake if more than 1 hour asleep (adjust as needed)
        if hours_asleep >= 1:
            self.wake_up()
            return True
        return False