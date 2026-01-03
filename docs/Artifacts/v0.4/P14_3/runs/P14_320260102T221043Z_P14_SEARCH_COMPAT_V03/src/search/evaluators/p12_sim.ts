/**
 * P12_SIM-backed evaluator (model-scoped).
 * - Uses P12-style metrics: selectivity S and crosstalk X on an oscillator-bank proxy.
 * - Optionally compiles an Intent via P13 compiler if present (for contract/executability surface),
 *   but scoring remains evaluator-local (safe, deterministic).
 *
 * Toy fallback is exported for wiring tests.
 */

import { LcgRng } from "../rng_lcg";

export type Fitness = number | { primary: number; [k: string]: any };

export type P12A2Intent = {
  kind: "A2";
  // oscillator bank
  n?: number;            // default 8
  target?: number;       // default 0
  omega0?: number;       // base omega default 2.0
  domega?: number;       // spacing default 0.25

  // drive params (the "gene" knobs)
  driveAmp: number;      // >= 0
  driveOmega?: number;   // default omega(target)

  // sim params
  dt?: number;           // default 1/240
  steps?: number;        // default 2400
  tailFrac?: number;     // default 0.25
};

export type P12ScoreDiag = {
  S: number;
  X: number;
  Etarget: number;
  EothersMean: number;
  EothersMax: number;
  programTokens?: number;
  compiled?: boolean;
};

function clamp(x: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, x));
}

function mean(xs: number[]) {
  return xs.reduce((a, b) => a + b, 0) / Math.max(1, xs.length);
}

/** P12 metric definitions (locked-formula compatible). */
export function selectivity(E: number[], k: number): number {
  const Ek = E[k] ?? 0;
  const others = E.filter((_, i) => i !== k);
  const denom = mean(others) || 1e-12;
  return Ek / denom;
}

export function crosstalk(E: number[], k: number): number {
  const Ek = E[k] ?? 0;
  const others = E.filter((_, i) => i !== k);
  const mx = Math.max(...others, 0);
  return mx / (Ek || 1e-12);
}

/**
 * Tiny deterministic oscillator-bank proxy.
 * x' = v
 * v' = -omega^2 x + drive(t)   (drive only on target)
 * Energy proxy (freq-normalized): E = x^2 + (v/omega)^2
 */
export function scoreP12A2(intent: P12A2Intent, seed = 1337): { fitness: { primary: number; S: number; X: number }; diag: P12ScoreDiag } {
  const n = intent.n ?? 8;
  const k = clamp(intent.target ?? 0, 0, n - 1) | 0;
  const omega0 = intent.omega0 ?? 2.0;
  const domega = intent.domega ?? 0.25;

  const omegas = Array.from({ length: n }, (_, i) => omega0 + domega * i);
  const omegaK = omegas[k];
  const driveOmega = intent.driveOmega ?? omegaK;

  const dt = intent.dt ?? (1 / 240);
  const steps = intent.steps ?? 2400;
  const tailFrac = clamp(intent.tailFrac ?? 0.25, 0.05, 0.9);
  const tailStart = Math.floor(steps * (1 - tailFrac));

  // compile (optional) — for contract/executability surface only
  let compiled = false;
  let programTokens: number | undefined;
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const mod: any = require("../../compiler/compile");
    const compileFn =
      mod?.compileIntent ??
      mod?.compile ??
      mod?.compileV0 ??
      mod?.default;
    if (typeof compileFn === "function") {
      const out: any = compileFn(intent);
      const prog = out?.program ?? out?.bundle?.program ?? out?.Program ?? out?.programV0;
      const tokens = prog?.tokens;
      if (Array.isArray(tokens)) programTokens = tokens.length;
      compiled = true;
    }
  } catch {
    // ignore
  }

  // state
  const x = Array.from({ length: n }, () => 0);
  const v = Array.from({ length: n }, () => 0);

  // deterministic tiny noise (keeps symmetry breaks stable)
  const rng = new LcgRng(seed);
  for (let i = 0; i < n; i++) {
    x[i] = (rng.float01() - 0.5) * 1e-6;
    v[i] = (rng.float01() - 0.5) * 1e-6;
  }

  // tail-averaged energies
  const Eacc = Array.from({ length: n }, () => 0);
  let tailCount = 0;

  for (let s = 0; s < steps; s++) {
    const t = s * dt;
    for (let i = 0; i < n; i++) {
      const om = omegas[i];
      const drive = (i === k) ? (intent.driveAmp * Math.sin(driveOmega * t)) : 0;
      const a = -(om * om) * x[i] + drive;
      v[i] += a * dt;
      x[i] += v[i] * dt;
    }

    if (s >= tailStart) {
      tailCount++;
      for (let i = 0; i < n; i++) {
        const om = omegas[i];
        const Ei = (x[i] * x[i]) + (v[i] / om) * (v[i] / om);
        Eacc[i] += Ei;
      }
    }
  }

  const E = Eacc.map(e => e / Math.max(1, tailCount));
  const S = selectivity(E, k);
  const X = crosstalk(E, k);

  // fitness: reward S, penalize X (stable monotone scalar)
  const primary = S / (1 + 5 * X);

  const others = E.filter((_, i) => i !== k);
  const diag: P12ScoreDiag = {
    S, X,
    Etarget: E[k] ?? 0,
    EothersMean: mean(others),
    EothersMax: Math.max(...others, 0),
    programTokens,
    compiled
  };

  return { fitness: { primary, S, X }, diag };
}

/** Toy fallback: maximize sum(bits) deterministically. */
export function scoreToyBits(bits: number[]): { fitness: { primary: number }; diag: any } {
  const primary = bits.reduce((a, b) => a + (b ? 1 : 0), 0);
  return { fitness: { primary }, diag: { ones: primary, len: bits.length } };
}

/** Deterministic gene helpers for A2 (driveAmp-only knob). */
export function initA2DriveAmp(rng: LcgRng): P12A2Intent {
  return {
    kind: "A2",
    n: 8,
    target: 0,
    omega0: 2.0,
    domega: 0.25,
    driveAmp: rng.float01() * 2.0, // [0,2]
    dt: 1 / 240,
    steps: 2400,
    tailFrac: 0.25
  };
}

export function stepA2DriveAmp(rng: LcgRng, g: P12A2Intent): P12A2Intent {
  // small symmetric perturb, clamp
  const delta = (rng.float01() - 0.5) * 0.4; // [-0.2,0.2]
  const next = { ...g, driveAmp: clamp(g.driveAmp + delta, 0, 3) };
  return next;
}
