/**
 * Stage B — Canonical metrics
 * Keep all tests using these functions so thresholds are consistent.
 */

export function mean(xs: number[]) {
  if (!xs.length) return 0;
  let s = 0;
  for (const x of xs) s += x;
  return s / xs.length;
}

export function variance(xs: number[]) {
  if (xs.length < 2) return 0;
  const m = mean(xs);
  let s2 = 0;
  for (const x of xs) {
    const d = x - m;
    s2 += d * d;
  }
  return s2 / (xs.length - 1);
}

export function stddev(xs: number[]) {
  return Math.sqrt(variance(xs));
}

/** Selectivity S = target / mean(others) */
export function selectivity(target: number, others: number[], eps = 1e-12) {
  return target / (mean(others) + eps);
}

/** Crosstalk X = max(others) / target */
export function crosstalk(target: number, others: number[], eps = 1e-12) {
  let mx = 0;
  for (const o of others) mx = Math.max(mx, o);
  return mx / (target + eps);
}

/** Δcoupling = match - mismatch (used by A3.1) */
export function deltaCoupling(match: number, mismatch: number) {
  return match - mismatch;
}

/**
 * Energy used by drive signal: E = ∑ u(t)^2 dt
 * (Cheap proxy; later you can swap for hardware-specific power models.)
 */
export function energyUsed(uSeries: number[], dt: number) {
  let e = 0;
  for (const u of uSeries) e += u * u * dt;
  return e;
}

/**
 * Rigidity from pairwise distance time-series.
 * Input: distSeries[t][pairIdx] (or a flattened vector per time)
 * Output: lower std => higher rigidity.
 */
export function rigidity(distSeries: number[][], eps = 1e-12) {
  if (!distSeries.length) return { mean: 0, std: 0, score: 0 };

  // flatten per-pair over time then average pair stats
  const P = distSeries[0]?.length ?? 0;
  if (!P) return { mean: 0, std: 0, score: 0 };

  let meanSum = 0;
  let stdSum = 0;

  for (let p = 0; p < P; p++) {
    const xs: number[] = [];
    for (let t = 0; t < distSeries.length; t++) xs.push(distSeries[t][p]);
    const m = mean(xs);
    const s = stddev(xs);
    meanSum += m;
    stdSum += s;
  }

  const mAll = meanSum / P;
  const sAll = stdSum / P;

  // score in (0,1], 1 = perfectly rigid
  const score = 1 / (1 + sAll / (mAll + eps));
  return { mean: mAll, std: sAll, score };
}

/**
 * Geometry error against a target vector of distances (per time).
 * Useful for cluster hold tests (C4 later).
 */
export function shapeError(current: number[], target: number[]) {
  const n = Math.min(current.length, target.length);
  if (!n) return 0;
  let s = 0;
  for (let i = 0; i < n; i++) {
    const d = current[i] - target[i];
    s += d * d;
  }
  return Math.sqrt(s / n);
}
