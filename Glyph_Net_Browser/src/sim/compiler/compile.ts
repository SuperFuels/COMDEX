import type { Intent, CompileOutputs, ThresholdsA2, ThresholdsA31 } from "./types";
import type { Program } from "../lexicon";

/**
 * P13 compiler v0: Intent -> Program (auditable codegen).
 * Scope: only A2 and A3.1 primitives, using existing lexicon/program execution.
 *
 * NOTE: lexicon Program shape is { tokens: Token[] }.
 */
export function compileIntent(intent: Intent): CompileOutputs {
  const created_utc = new Date().toISOString();

  if (intent.target === "A2") {
    const A = intent.amp ?? 1.0;
    const phi = intent.phase ?? 0.0;
    const gate = intent.gate ?? 1.0;

    // Minimal A2: env is a sinusoid at omegaHz with amplitude A and phase phi.
    // We also include ω token for auditability, but env carries the actual drive function.
    const program: Program = {
      tokens: [
        { kind: "τ", t0: 0, t1: Infinity },
        { kind: "ω", omegaHz: intent.omegaHz },
        { kind: "A", A },
        { kind: "φ", phi },
        // Optional gating: encode gate as parity-like scalar in m(x) so it is auditable.
        // (If lexicon currently ignores this, it is still a pinned field for later extension.)
        { kind: "m(x)", tag: "gate", value: gate } as any,
        {
          kind: "env",
          mode: "sin",
          omegaHz: intent.omegaHz,
          A,
          phi,
        } as any,
      ],
    };

    const thresholds: ThresholdsA2 = {
      selectivity_min: 5.0,
      crosstalk_max: 0.25,
    };

    return {
      program,
      thresholds,
      meta: {
        target: "A2",
        seed: intent.seed,
        created_utc,
        compiler_version: "v0",
        note: intent.note,
      },
    };
  }

  // A3.1: handshake/gate/chirality as lexicon tokens (auditable even if partially used).
  const gate = intent.gate ?? 1.0;

  const program: Program = {
    tokens: [
      { kind: "τ", t0: 0, t1: Infinity },
      { kind: "p", parity: intent.chiralityA === intent.chiralityB ? 1 : -1 } as any,
      { kind: "m(x)", tag: "gate", value: gate } as any,
      {
        kind: "env",
        mode: "handshake",
        a: intent.a,
        b: intent.b,
        chiralityA: intent.chiralityA,
        chiralityB: intent.chiralityB,
        gate,
      } as any,
    ],
  };

  const thresholds: ThresholdsA31 = {
    match_lock_min: 0.55,
    mismatch_lock_max: 0.35,
    drift_ratio_max: 0.6,
  };

  return {
    program,
    thresholds,
    meta: {
      target: "A31",
      seed: intent.seed,
      created_utc,
      compiler_version: "v0",
      note: intent.note,
    },
  };
}

export function toCompileBundleJSON(o: CompileOutputs): string {
  return JSON.stringify(o, null, 2) + "\n";
}
