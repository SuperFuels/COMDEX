"""
🎛 UCS Orchestrator
-----------------------------------------------------
Handles:
    * Multi-container execution sequences (Quantum Orb -> Vortex -> Black Hole -> Torus)
    * SQI-linked GPIO pulse triggers for physical Pi bench experiments
    * Integration with UCSRuntime for container execution
"""

import time

class UCSOrchestrator:
    def __init__(self, runtime):
        """
        :param runtime: An active UCSRuntime instance
        """
        self.runtime = runtime
        self.chain = []

    # ---------------------------------------------------------
    # 🔗 Chain Definition & Execution
    # ---------------------------------------------------------
    def define_chain(self, sequence):
        """
        Define container flow sequence.
        Example:
            ["Quantum Orb", "Vortex", "Black Hole", "Torus"]
        """
        self.chain = sequence
        print(f"🔗 Chain defined: {' -> '.join(sequence)}")

    def execute_chain(self, delay: float = 0.5):
        """
        Execute defined chain with pacing delay between containers.
        Triggers each container's runtime logic in sequence.
        """
        for name in self.chain:
            self.runtime.run_container(name)
            self.trigger_sqi_pulse(name)  # 🔥 Pulse check per stage
            time.sleep(delay)
        print("✅ Chain execution complete.")

    # ---------------------------------------------------------
    # ⚡ SQI -> GPIO Pulse Integration
    # ---------------------------------------------------------
    def trigger_sqi_pulse(self, container_id: str):
        """
        Emits an SQI-linked GPIO pulse when container output reaches exhaust stage.
        Specifically fires for Torus geometry (symbolic exhaust stage).
        """
        data = self.runtime.get_container(container_id)
        if not data:
            print(f"[SQI] ⚠ No container data found for: {container_id}")
            return

        geometry = data.get("geometry", "")
        if geometry == "Torus":
            print(f"[SQI] 🔥 Emitting GPIO pulse from {container_id} (Torus exhaust)")
            # TODO: Hook actual Raspberry Pi GPIO here
            self.runtime.emit_event("gpio_pulse", data)
        else:
            print(f"[SQI] Skipped GPIO pulse (geometry={geometry})")

    # ---------------------------------------------------------
    # 🧩 Chain Reset
    # ---------------------------------------------------------
    def reset_chain(self):
        """Clear the current execution chain."""
        self.chain = []
        print("🔄 Chain reset.")