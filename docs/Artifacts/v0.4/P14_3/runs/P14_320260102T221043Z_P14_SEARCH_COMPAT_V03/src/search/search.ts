import { LcgRng, makeLCG } from "./rng_lcg";

/**
 * Compatibility-first search core.
 *
 * Newer code wants: best, bestFitness, traceBestScalar
 * Older smoke/bundle wants: best_candidate, best_fitness, best_score_trace, best_pass_trace
 *
 * We emit BOTH.
 */
export type Fitness =
  | number
  | { primary?: number; score?: number; pass?: boolean; [k: string]: any };

export type SearchConfig<TCandidate> = {
  seed: number;

  // --- init/sample (compat) ---
  sample?: (rng: LcgRng) => TCandidate;
  init?: (rng: LcgRng) => TCandidate;
  make?: (rng: LcgRng) => TCandidate;

  // --- objective (compat) ---
  evaluate?: (c: TCandidate) => Fitness;
  score?: (c: TCandidate) => Fitness;
  fitness?: (c: TCandidate) => Fitness;

  // --- mutation / step proposal (compat) ---
  // IMPORTANT: legacy tests expect mutate(rng, cur, step)
  mutate?: (rng: LcgRng, c: TCandidate, step: number) => TCandidate;
  step?: (rng: LcgRng, c: TCandidate, step: number) => TCandidate;
  perturb?: (rng: LcgRng, c: TCandidate, step: number) => TCandidate;

  // --- hillclimb knobs ---
  iters: number;
  step0?: number;
  step_decay?: number;

  // legacy stop gate (optional)
  stop_when?: { pass?: boolean };
};

export type SearchResult<TCandidate> = {
  // --- new fields ---
  best: TCandidate;
  bestFitness: Fitness;
  traceBestScalar: number[];
  meta: {
    seed: number;
    iters: number;
    step0?: number;
    step_decay?: number;
  };

  // --- legacy fields (required by old smoke/bundle) ---
  best_candidate: TCandidate;
  best_fitness: Fitness;
  best_score_trace: number[];
  best_pass_trace: boolean[];
};

function scalarOf(f: Fitness): number {
  if (typeof f === "number") return f;
  if (typeof f.primary === "number") return f.primary;
  if (typeof f.score === "number") return f.score;
  return 0;
}

function passOf(f: Fitness): boolean {
  return typeof f === "object" && !!f && f.pass === true;
}

function resolveSample<T>(cfg: SearchConfig<T>): (rng: LcgRng) => T {
  const fn = cfg.sample ?? cfg.init ?? cfg.make;
  if (!fn) throw new Error("SearchConfig missing sample/init/make");
  return fn;
}

function resolveEval<T>(cfg: SearchConfig<T>): (c: T) => Fitness {
  const fn = cfg.evaluate ?? cfg.score ?? cfg.fitness;
  if (!fn) throw new Error("SearchConfig missing evaluate/score/fitness");
  return fn;
}

function resolveMutate<T>(
  cfg: SearchConfig<T>
): (rng: LcgRng, c: T, step: number) => T {
  const fn = cfg.mutate ?? cfg.step ?? cfg.perturb;
  if (!fn) throw new Error("SearchConfig missing mutate/step/perturb");
  return fn;
}

/**
 * Hillclimb local search (deterministic for fixed seed + cfg).
 * Emits legacy traces + new scalar trace.
 */
export function hillclimb<TCandidate>(
  cfg: SearchConfig<TCandidate>
): SearchResult<TCandidate> {
  const rng = makeLCG(cfg.seed);
  const sample = resolveSample(cfg);
  const evaluate = resolveEval(cfg);
  const mutate = resolveMutate(cfg);

  const step0 = cfg.step0 ?? 1.0;
  const step_decay = cfg.step_decay ?? 0.995;

  let cur = sample(rng);
  let curFit = evaluate(cur);
  let curScore = scalarOf(curFit);

  let best = cur;
  let bestFit = curFit;
  let bestScore = curScore;
  let bestPass = passOf(bestFit);

  const best_score_trace: number[] = [bestScore];
  const best_pass_trace: boolean[] = [bestPass];

  let step = step0;
  for (let i = 0; i < cfg.iters; i++) {
    // legacy order: mutate(rng, cur, step)
    const cand = mutate(rng, cur, step);
    const candFit = evaluate(cand);
    const candScore = scalarOf(candFit);

    if (candScore >= curScore) {
      cur = cand;
      curFit = candFit;
      curScore = candScore;

      if (candScore >= bestScore) {
        best = cand;
        bestFit = candFit;
        bestScore = candScore;
        bestPass = passOf(bestFit);
      }
    }

    best_score_trace.push(bestScore);
    best_pass_trace.push(bestPass);

    if (cfg.stop_when?.pass && bestPass) {
      // keep traces deterministic: still decay step and continue pushing same best
      // (do not break; legacy smoke doesn't require early stop)
    }

    step *= step_decay;
  }

  const traceBestScalar = best_score_trace.slice();

  return {
    // new
    best,
    bestFitness: bestFit,
    traceBestScalar,
    meta: { seed: cfg.seed, iters: cfg.iters, step0, step_decay },

    // legacy
    best_candidate: best,
    best_fitness: bestFit,
    best_score_trace,
    best_pass_trace,
  };
}

/**
 * Random search baseline (deterministic for fixed seed + cfg).
 * Emits legacy traces + new scalar trace.
 */
export function randomSearch<TCandidate>(
  cfg: Omit<
    SearchConfig<TCandidate>,
    "mutate" | "step" | "perturb" | "step0" | "step_decay"
  >
): SearchResult<TCandidate> {
  const rng = makeLCG(cfg.seed);
  const sample = resolveSample(cfg as any);
  const evaluate = resolveEval(cfg as any);

  let best = sample(rng);
  let bestFit = evaluate(best);
  let bestScore = scalarOf(bestFit);
  let bestPass = passOf(bestFit);

  const best_score_trace: number[] = [bestScore];
  const best_pass_trace: boolean[] = [bestPass];

  for (let i = 0; i < cfg.iters; i++) {
    const cand = sample(rng);
    const candFit = evaluate(cand);
    const candScore = scalarOf(candFit);

    if (candScore >= bestScore) {
      best = cand;
      bestFit = candFit;
      bestScore = candScore;
      bestPass = passOf(bestFit);
    }

    best_score_trace.push(bestScore);
    best_pass_trace.push(bestPass);
  }

  const traceBestScalar = best_score_trace.slice();

  return {
    // new
    best,
    bestFitness: bestFit,
    traceBestScalar,
    meta: { seed: cfg.seed, iters: cfg.iters },

    // legacy
    best_candidate: best,
    best_fitness: bestFit,
    best_score_trace,
    best_pass_trace,
  };
}
