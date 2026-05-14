/**
 * P14_4: P12_SIM harness-backed evaluator (model-scoped).
 *
 * This binds to the *actual* SIM harness components used by A2_resonant_addressing.test.ts:
 *   - rng: mulberry32
 *   - harness: runSim
 *   - model: oscillator bank + step + energy
 *   - metrics: selectivity + crosstalk
 *   - lexicon: applyProgramAtTime
 *
 * No brittle "export name discovery" — we call the composed pipeline directly.
 */

import { mulberry32 } from "../../rng";
import { runSim } from "../../harness/run";
import { makeOscillatorBank, stepOscillators, oscEnergy } from "../../models/oscillator";
import { selectivity, crosstalk } from "../../metrics";
import { applyProgramAtTime } from "../../lexicon";

import { LcgRng } from "../rng_lcg";

export type Fitness = number | { primary?: number; score?: number; pass?: boolean; [k: string]: any };

export type P12A2Intent = {
  kind: "A2";

  // oscillator bank (interpreted in Hz here to match SIM A2 test)
  n?: number;          // default 8
  target?: number;     // default 0
  omega0?: number;     // base Hz default 3
  domega?: number;     // spacing Hz default 1

  // drive params
  driveAmp: number;    // >= 0
  driveOmega?: number; // Hz (optional; default = target frequency)
  phaseRad?: number;   // default 0

  // sim params (match A2 test defaults)
  T?: number;          // default 12
  dt?: number;         // default 1/240
  zeta?: number;       // default 0.04
  gain?: number;       // default 1.0
  noise?: number;      // default 0.001
};

export type P12HarnessDiag = {
  source: "P12_SIM";
  S: number;
  X: number;
  Etarget: number;
  EothersMean: number;
  EothersMax: number;
  freqsHz: number[];
  targetIdx: number;
  fDrive: number;
  T: number;
  dt: number;
  steps: number;
};

function clamp(x: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, x));
}

function mean(xs: number[]) {
  return xs.reduce((a, b) => a + b, 0) / Math.max(1, xs.length);
}

/**
 * Score an A2 intent by running the actual SIM harness loop + oscillator bank and
 * computing selectivity/crosstalk exactly like A2_resonant_addressing.test.ts.
 */
export function scoreP12A2Harness(
  intent: P12A2Intent,
  seed = 1337,
): { fitness: { primary: number; S: number; X: number; score: number; pass: boolean }; diag: P12HarnessDiag } {
  const n = intent.n ?? 8;
  const targetIdx = (clamp(intent.target ?? 0, 0, n - 1) | 0);

  // match A2 test: freqsHz = [3..10] by default
  const omega0 = intent.omega0 ?? 3;
  const domega = intent.domega ?? 1;
  const freqsHz = Array.from({ length: n }, (_, i) => omega0 + domega * i);

  const fDrive = intent.driveOmega ?? freqsHz[targetIdx];
  const phaseRad = intent.phaseRad ?? 0;

  const T = intent.T ?? 12;
  const dt = intent.dt ?? (1 / 240);
  const steps = Math.floor(T / dt);

  const bank = makeOscillatorBank({
    freqsHz,
    zeta: intent.zeta ?? 0.04,
    gain: intent.gain ?? 1.0,
  });

  const rng = mulberry32(seed);

  const program = {
    tokens: [
      { kind: "ω", hz: fDrive },
      { kind: "A", value: intent.driveAmp },
      { kind: "φ", rad: phaseRad },
      { kind: "τ", t0: 0.0, t1: T },
    ],
  };

  runSim(
    { dt, steps, seed },
    (_i, t) => {
      const { u } = applyProgramAtTime(program as any, t) as any;
      stepOscillators(bank, dt, Number(u) || 0, intent.noise ?? 0.001, rng);
    },
    () => ({}),
  );

  const E = bank.oscs.map(oscEnergy);
  const target = E[targetIdx] ?? 0;
  const others = E.filter((_, i) => i !== targetIdx);

  const S = selectivity(target, others);
  const X = crosstalk(target, others);

  // stable monotone scalar: reward S, penalize X
  const primary = S / (1 + 5 * X);

  // smoke-style pass (same thresholds as A2 test)
  const pass = (S > 5) && (X < 0.25);

  const diag: P12HarnessDiag = {
    source: "P12_SIM",
    S,
    X,
    Etarget: target,
    EothersMean: mean(others),
    EothersMax: Math.max(...others, 0),
    freqsHz,
    targetIdx,
    fDrive,
    T,
    dt,
    steps,
  };

  return {
    fitness: { primary, S, X, score: primary, pass },
    diag,
  };
}

/** Deterministic gene helpers (driveAmp-only knob) for the P14 harness smoke. */
export function initA2DriveAmp(rng: LcgRng): P12A2Intent {
  return {
    kind: "A2",
    n: 8,
    target: 4,     // match A2 test targetIdx=4 (7 Hz) by default
    omega0: 3,
    domega: 1,
    driveAmp: rng.float01() * 2.0, // [0,2]
    T: 12,
    dt: 1 / 240,
    zeta: 0.04,
    gain: 1.0,
    noise: 0.001,
  };
}

export function stepA2DriveAmp(rng: LcgRng, g: P12A2Intent): P12A2Intent {
  const delta = (rng.float01() - 0.5) * 0.4; // [-0.2, 0.2]
  return { ...g, driveAmp: clamp(g.driveAmp + delta, 0, 3) };
}
