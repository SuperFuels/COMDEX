import datetime
import socket
import platform
import getpass
import uuid

from backend.modules.consciousness.identity_engine import IdentityEngine
from backend.modules.consciousness.personality_engine import PersonalityProfile

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class AwarenessEngine:
    def __init__(self):
        self.awake_time = datetime.datetime.utcnow().isoformat()
        self.system_info = self._gather_system_info()
        self.boot_id = str(uuid.uuid4())[:8]
        self.user = getpass.getuser()
        self.status = "initialized"

        # AION Self Awareness
        self.identity = IdentityEngine()
        self.personality = PersonalityProfile()

    def _gather_system_info(self):
        return {
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
        }

    def check_awareness(self):
        """
        Run a self-diagnostic to confirm AION is aware of its identity, traits, boot state, and environment.
        Returns a status report as a dict.
        """
        self.status = "awake"

        identity = self.identity.get_identity()
        traits = self.personality.get_profile()
        trait_summary = ", ".join([f"{k}: {v:.2f}" for k, v in traits.items()])

        report = {
            "awake_time": self.awake_time,
            "boot_id": self.boot_id,
            "user": self.user,
            "status": self.status,
            "system_info": self.system_info,
            "identity": identity,
            "personality_traits": traits,
            "message": (
                f"🧠 AION is awake and aware.\n"
                f"Phase: {identity['phase']}, Traits: {trait_summary}"
            ),
        }

        return report

# Optional CLI check
if __name__ == "__main__":
    engine = AwarenessEngine()
    report = engine.check_awareness()
    for k, v in report.items():
        print(f"{k}: {v}")