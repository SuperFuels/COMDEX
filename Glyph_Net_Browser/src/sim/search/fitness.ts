/**
 * P14 search fitness contract (evaluator-injected).
 * Keep this file model-agnostic: SIM/engine evaluators should map into this shape.
 */

export type FitnessVector = {
  // Higher is better
  primary: number;

  // Lower is better
  crosstalk?: number;
  energy?: number;
  drift?: number;

  // Optional hard constraint flag
  feasible?: boolean;
};

export type FitnessWeights = {
  wPrimary?: number;
  wCrosstalk?: number;
  wEnergy?: number;
  wDrift?: number;

  // Penalty applied when feasible === false
  infeasiblePenalty?: number;
};

export function scalarizeFitness(
  f: FitnessVector,
  w: FitnessWeights = {},
): number {
  const {
    wPrimary = 1,
    wCrosstalk = 1,
    wEnergy = 1,
    wDrift = 1,
    infeasiblePenalty = 1e9,
  } = w;

  let s = 0;
  s += wPrimary * f.primary;

  if (typeof f.crosstalk === "number") s -= wCrosstalk * f.crosstalk;
  if (typeof f.energy === "number") s -= wEnergy * f.energy;
  if (typeof f.drift === "number") s -= wDrift * f.drift;

  if (f.feasible === false) s -= infeasiblePenalty;
  return s;
}

export function betterThan(
  a: FitnessVector,
  b: FitnessVector,
  w?: FitnessWeights,
): boolean {
  return scalarizeFitness(a, w) > scalarizeFitness(b, w);
}
