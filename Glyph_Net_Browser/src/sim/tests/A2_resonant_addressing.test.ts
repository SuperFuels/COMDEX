import { describe, it, expect } from "vitest";
import { mulberry32 } from "../rng";
import { runSim } from "../harness/run";
import { makeOscillatorBank, stepOscillators, oscEnergy } from "../models/oscillator";
import { selectivity, crosstalk } from "../metrics";
import { applyProgramAtTime } from "../lexicon";

type WaveToken =
  | { kind: "ω"; hz: number }
  | { kind: "A"; value: number }
  | { kind: "φ"; rad: number }
  | { kind: "τ"; t0: number; t1: number };

type WaveProgram = { tokens: WaveToken[] };

describe("A2 Resonant Addressing (SIM)", () => {
  it("driving f_k selectively excites node k (via Lexicon program)", () => {
    const seed = 1337;
    const rng = mulberry32(seed);

    // wider observation window reduces τ-window leakage; lower damping sharpens resonance
    const freqsHz = [3, 4, 5, 6, 7, 8, 9, 10];
    const bank = makeOscillatorBank({ freqsHz, zeta: 0.04, gain: 1.0 });

    const targetIdx = 4; // 7 Hz
    const fDrive = freqsHz[targetIdx];

    const T = 12; // longer => narrower spectral main lobe
    const program: WaveProgram = {
      tokens: [
        { kind: "ω", hz: fDrive },
        { kind: "A", value: 1.0 },
        { kind: "φ", rad: 0.0 },
        { kind: "τ", t0: 0.0, t1: T },
      ],
    };

    const dt = 1 / 240;
    const steps = Math.floor(T / dt);

    runSim(
      { dt, steps, seed },
      (_i, t) => {
        const { u } = applyProgramAtTime(program as any, t) as any;
        stepOscillators(bank, dt, Number(u) || 0, 0.001, rng);
      },
      () => ({}),
    );

    const E = bank.oscs.map(oscEnergy);
    const target = E[targetIdx];
    const others = E.filter((_, i) => i !== targetIdx);

    const S = selectivity(target, others);
    const X = crosstalk(target, others);

    expect(S).toBeGreaterThan(5);
    expect(X).toBeLessThan(0.25);
  });
});
