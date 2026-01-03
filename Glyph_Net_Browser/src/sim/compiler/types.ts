import type { Program } from "../lexicon";

export type CompileTarget = "A2" | "A31";

export type IntentCommon = {
  target: CompileTarget;
  note?: string;
  // audit pins
  seed: number;
};

export type IntentA2 = IntentCommon & {
  target: "A2";
  nodeIndex: number;   // which oscillator/node to address
  omegaHz: number;     // drive frequency (Hz)
  amp?: number;        // drive amplitude (default 1.0)
  phase?: number;      // radians (default 0)
  gate?: number;       // 0..1 (default 1)
};

export type IntentA31 = IntentCommon & {
  target: "A31";
  a: number;
  b: number;
  chiralityA: 1 | -1;
  chiralityB: 1 | -1;
  gate?: number;       // 0..1 (default 1)
};

export type Intent = IntentA2 | IntentA31;

export type ThresholdsA2 = {
  selectivity_min: number;
  crosstalk_max: number;
};

export type ThresholdsA31 = {
  match_lock_min: number;
  mismatch_lock_max: number;
  drift_ratio_max: number;
};

export type CompileOutputs = {
  program: Program;
  thresholds: ThresholdsA2 | ThresholdsA31;
  meta: {
    target: CompileTarget;
    seed: number;
    created_utc: string;
    compiler_version: "v0";
    note?: string;
  };
};
