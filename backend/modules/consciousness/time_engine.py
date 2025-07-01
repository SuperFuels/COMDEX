import datetime
import random

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
