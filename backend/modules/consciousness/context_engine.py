import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class ContextEngine:
    """
    Tracks AION's temporal, spatial, and situational context for grounding decisions.
    """

    def __init__(self):
        self.context = {
            "datetime": str(datetime.datetime.now()),
            "location": "unknown",
            "environment": "default",
            "last_event": None
        }

    def update_time(self):
        self.context["datetime"] = str(datetime.datetime.now())

    def set_location(self, location):
        self.context["location"] = location

    def set_environment(self, environment):
        self.context["environment"] = environment

    def log_event(self, event_name):
        self.context["last_event"] = {
            "event": event_name,
            "timestamp": str(datetime.datetime.now())
        }

    def get_context(self):
        self.update_time()
        return self.context

    def describe_context(self):
        self.update_time()
        return (
            f"AION is currently at '{self.context['location']}' in a "
            f"'{self.context['environment']}' environment. The last event was "
            f"'{self.context['last_event']}'."
        )
