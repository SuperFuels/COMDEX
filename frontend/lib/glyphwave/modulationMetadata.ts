// File: frontend/lib/glyphwave/modulationMetadata.ts

export enum ModulationStrategy {
  SIM_PHASE = "simulated_phase_shift",
  WDM = "wavelength_division_multiplexing",
  QKD_PHASE = "qkd_phase_modulation",
  QAM = "quantum_amplitude_modulation",
  SYMBOLIC_OVERLAY = "symbolic_overlay_encoding",
  POLARIZATION = "photon_polarization_shift",
  ENTANGLED_FORK = "entangled_wave_forking",
  NOISE_CARRIER = "chaotic_noise_spread",
}

export const MODULATION_METADATA: Record<ModulationStrategy, {
  icon: string;
  description: string;
  security_score: number; // 0–10
  coherence_penalty: number; // 0–1
}> = {
  [ModulationStrategy.SIM_PHASE]: {
    icon: "🌀",
    description: "Virtual beam phase shifts (testing mode)",
    security_score: 1,
    coherence_penalty: 0.1,
  },
  [ModulationStrategy.WDM]: {
    icon: "🌈",
    description: "Wavelength division for multi-symbol transport",
    security_score: 4,
    coherence_penalty: 0.2,
  },
  [ModulationStrategy.QKD_PHASE]: {
    icon: "🔐",
    description: "Phase-modulated secure quantum link (QKD)",
    security_score: 10,
    coherence_penalty: 0.05,
  },
  [ModulationStrategy.QAM]: {
    icon: "📶",
    description: "Amplitude-encoded glyphs using quantum amplitudes",
    security_score: 6,
    coherence_penalty: 0.25,
  },
  [ModulationStrategy.SYMBOLIC_OVERLAY]: {
    icon: "🧠",
    description: "Layered symbolic compression on base beam",
    security_score: 8,
    coherence_penalty: 0.3,
  },
  [ModulationStrategy.POLARIZATION]: {
    icon: "🧲",
    description: "Photon polarization for QWave modulation",
    security_score: 7,
    coherence_penalty: 0.2,
  },
  [ModulationStrategy.ENTANGLED_FORK]: {
    icon: "🌐",
    description: "Forked entangled beam split with addressable threads",
    security_score: 9,
    coherence_penalty: 0.15,
  },
  [ModulationStrategy.NOISE_CARRIER]: {
    icon: "💥",
    description: "Chaos-encoded wave pattern for obfuscation",
    security_score: 5,
    coherence_penalty: 0.5,
  },
};