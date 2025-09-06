from enum import Enum
from typing import Dict, Any, Tuple
from .carrier_types import CarrierType
from .modulation_strategies import ModulationStrategy


class CarrierScheduler:
    # Static data
    policy_matrix = {
        "secure": {
            "preferred_carrier": CarrierType.QUANTUM,
            "modulation": ModulationStrategy.QKD_PHASE,
        },
        "high_fidelity": {
            "preferred_carrier": CarrierType.OPTICAL,
            "modulation": ModulationStrategy.WDM,
        },
        "dream_mutation": {
            "preferred_carrier": CarrierType.SIMULATED,
            "modulation": ModulationStrategy.SYMBOLIC_OVERLAY,
        },
        "broadcast": {
            "preferred_carrier": CarrierType.RADIO,
            "modulation": ModulationStrategy.NOISE_CARRIER,
        },
        "default": {
            "preferred_carrier": CarrierType.SIMULATED,
            "modulation": ModulationStrategy.SIM_PHASE,
        },
    }

    carrier_profiles = {
        CarrierType.QUANTUM: {"latency_ms": 0.5, "coherence": 0.99},
        CarrierType.OPTICAL: {"latency_ms": 1.2, "coherence": 0.92},
        CarrierType.SIMULATED: {"latency_ms": 3.5, "coherence": 0.85},
        CarrierType.RADIO: {"latency_ms": 8.0, "coherence": 0.70},
    }

    @staticmethod
    def score_carrier(carrier: Dict[str, Any], goal_fidelity: str) -> float:
        """
        Score how well this carrier matches the symbolic goal.
        """
        coherence = carrier.get("coherence", 0.5)

        target = {
            "precise": 0.9,
            "symbolic": 0.6,
            "balanced": 0.75,
        }.get(goal_fidelity, 0.75)

        return 1.0 - abs(target - coherence)

    @staticmethod
    def select(
        payload: Dict[str, Any],
        sender_id: str,
        recipient_id: str,
        context: Dict[str, Any]
    ) -> Tuple[CarrierType, ModulationStrategy]:
        """
        Select the best carrier and modulation strategy for the current symbolic context.
        """
        intent = context.get("intent", "default")
        security_required = context.get("qkd_required", False)
        goal = context.get("goal_fidelity", "balanced")

        # Force QKD if required
        if security_required:
            return CarrierType.QUANTUM, ModulationStrategy.QKD_PHASE

        # Evaluate carriers
        available = []
        for carrier_type, profile in CarrierScheduler.carrier_profiles.items():
            score = CarrierScheduler.score_carrier(profile, goal)
            modulation = CarrierScheduler.policy_matrix.get(intent, CarrierScheduler.policy_matrix["default"])["modulation"]
            available.append({
                "carrier_type": carrier_type,
                "modulation": modulation,
                "latency_ms": profile["latency_ms"],
                "coherence": profile["coherence"],
                "score": score,
            })

        best = max(available, key=lambda c: c["score"])
        return best["carrier_type"], best["modulation"]