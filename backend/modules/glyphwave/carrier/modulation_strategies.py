from enum import Enum
from dataclasses import dataclass
from typing import Dict


class ModulationStrategy(str, Enum):
    SIM_PHASE = "simulated_phase_shift"
    WDM = "wavelength_division_multiplexing"
    QKD_PHASE = "qkd_phase_modulation"
    QAM = "quantum_amplitude_modulation"
    SYMBOLIC_OVERLAY = "symbolic_overlay_encoding"
    POLARIZATION = "photon_polarization_shift"
    ENTANGLED_FORK = "entangled_wave_forking"
    NOISE_CARRIER = "chaotic_noise_spread"

    def description(self) -> str:
        return {
            self.SIM_PHASE: "Virtual beam phase shifts (testing mode)",
            self.WDM: "Wavelength division for multi-symbol transport",
            self.QKD_PHASE: "Phase-modulated secure quantum link (QKD)",
            self.QAM: "Amplitude-encoded glyphs using quantum amplitudes",
            self.SYMBOLIC_OVERLAY: "Layered symbolic compression on base beam",
            self.POLARIZATION: "Photon polarization for QWave modulation",
            self.ENTANGLED_FORK: "Forked entangled beam split with addressable threads",
            self.NOISE_CARRIER: "Chaos-encoded wave pattern for obfuscation",
        }[self]


@dataclass
class ModulationInfo:
    description: str
    coherence_penalty: float  # e.g. 0.1 = 10% coherence loss
    security_score: int       # 0-5 scale
    optical_required: bool
    symbolic_mode: bool


MODULATION_METADATA: Dict[ModulationStrategy, ModulationInfo] = {
    ModulationStrategy.SIM_PHASE: ModulationInfo(
        description=ModulationStrategy.SIM_PHASE.description(),
        coherence_penalty=0.2,
        security_score=1,
        optical_required=False,
        symbolic_mode=False
    ),
    ModulationStrategy.WDM: ModulationInfo(
        description=ModulationStrategy.WDM.description(),
        coherence_penalty=0.05,
        security_score=2,
        optical_required=True,
        symbolic_mode=False
    ),
    ModulationStrategy.QKD_PHASE: ModulationInfo(
        description=ModulationStrategy.QKD_PHASE.description(),
        coherence_penalty=0.01,
        security_score=5,
        optical_required=True,
        symbolic_mode=False
    ),
    ModulationStrategy.QAM: ModulationInfo(
        description=ModulationStrategy.QAM.description(),
        coherence_penalty=0.08,
        security_score=4,
        optical_required=True,
        symbolic_mode=False
    ),
    ModulationStrategy.SYMBOLIC_OVERLAY: ModulationInfo(
        description=ModulationStrategy.SYMBOLIC_OVERLAY.description(),
        coherence_penalty=0.12,
        security_score=1,
        optical_required=False,
        symbolic_mode=True
    ),
    ModulationStrategy.POLARIZATION: ModulationInfo(
        description=ModulationStrategy.POLARIZATION.description(),
        coherence_penalty=0.03,
        security_score=4,
        optical_required=True,
        symbolic_mode=False
    ),
    ModulationStrategy.ENTANGLED_FORK: ModulationInfo(
        description=ModulationStrategy.ENTANGLED_FORK.description(),
        coherence_penalty=0.06,
        security_score=3,
        optical_required=False,
        symbolic_mode=True
    ),
    ModulationStrategy.NOISE_CARRIER: ModulationInfo(
        description=ModulationStrategy.NOISE_CARRIER.description(),
        coherence_penalty=0.25,
        security_score=2,
        optical_required=False,
        symbolic_mode=True
    ),
}