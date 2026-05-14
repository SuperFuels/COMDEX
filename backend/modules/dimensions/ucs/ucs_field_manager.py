import math
from typing import Dict, Any

class UCSFieldManager:
    """
    UCS Field Manager:
    - Controls simulated environmental fields (gravity, EM, wave intensity).
    - Provides real-time adjustable field states for experiments.
    - Integrates with SEC/QWave engines for dynamic physics effects.
    """

    def __init__(self):
        self.fields: Dict[str, float] = {
            "gravity": 1.0,
            "magnetic": 0.0,
            "wave_intensity": 0.0
        }
        self.container = None
        self.time_accumulator = 0.0

    def initialize_fields(self, field_config: Dict[str, float]):
        """Initialize fields with provided configuration."""
        for field, value in field_config.items():
            self.fields[field] = value
        print(f"[UCSFieldManager] Fields initialized: {self.fields}")

    def link_to_container(self, container):
        """Attach field manager to parent SEC container."""
        self.container = container
        print(f"[UCSFieldManager] Linked to container: {container.container_id}")

    def update_fields(self, delta_time: float):
        """
        Update dynamic field states over time.
        Gravity may oscillate, waves pulse, EM fluctuates based on runtime load.
        """
        self.time_accumulator += delta_time

        # Simulated wave pulsing (sinusoidal intensity)
        if "wave_intensity" in self.fields:
            wave_base = self.fields["wave_intensity"]
            self.fields["wave_intensity"] = wave_base + 0.2 * math.sin(self.time_accumulator * 2.0)

        # EM field fluctuations (minor noise-based variation)
        if "magnetic" in self.fields:
            self.fields["magnetic"] += 0.01 * math.sin(self.time_accumulator * 1.5)

        # Debug output for HUD sync
        self._broadcast_field_states()

    def adjust_field(self, field: str, value: float):
        """Adjust a field manually in real time (HUD control)."""
        if field in self.fields:
            self.fields[field] = value
            print(f"[UCSFieldManager] Field adjusted: {field} -> {value}")
        else:
            print(f"[UCSFieldManager] Unknown field: {field}")

    def get_flow_force(self, source_id: str, target_id: str) -> float:
        """
        Calculate flow force between containers based on gravity/EM fields.
        Example: Protons moving from generator -> accelerator.
        """
        gravity = self.fields.get("gravity", 1.0)
        em = self.fields.get("magnetic", 0.0)
        wave = self.fields.get("wave_intensity", 0.0)
        force = (gravity * 0.6) + (em * 0.3) + (wave * 0.1)
        return max(force, 0.0)

    def shutdown_fields(self):
        """Disable all active fields."""
        for key in self.fields.keys():
            self.fields[key] = 0.0
        print(f"[UCSFieldManager] Fields shut down.")

    def _broadcast_field_states(self):
        """Broadcast current field states to frontend HUD."""
        if self.container:
            self.container.log_event(
                f"📡 Field Update -> Gravity: {self.fields['gravity']:.2f}, "
                f"EM: {self.fields['magnetic']:.2f}, Wave: {self.fields['wave_intensity']:.2f}"
            )