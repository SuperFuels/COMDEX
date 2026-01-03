import { LcgRng, makeLCG } from "./rng_lcg";

export type Fitness = number | { primary: number; [k: string]: any };

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
  // Accept either:
  //   (candidate, rng, step)  OR (rng, candidate, step)
  // and also common 2-arg forms:
  //   (candidate, rng) OR (rng, candidate)
  mutate?: any;
  step?: any;
  perturb?: any;

  // --- hillclimb knobs ---
  iters: number;
  step0?: number;
  step_decay?: number;
};

export type SearchResult<TCandidate> = {
  best: TCandidate;
  bestFitness: Fitness;
  traceBestScalar: number[];
  meta: {
    seed: number;
    iters: number;
    step0?: number;
    step_decay?: number;
  };
};

function primaryScalar(f: Fitness): number {
  return typeof f === "number" ? f : (f.primary ?? 0);
}

function resolveSample<T>(cfg: SearchConfig<T>): (rng: LcgRng) => T {
  const fn = cfg.sample ?? cfg.init ?? cfg.make;
  if (!fn) throw new Error("SearchConfig missing init/sample/make");
  return fn;
}

function resolveEval<T>(cfg: SearchConfig<T>): (c: T) => Fitness {
  const fn = cfg.evaluate ?? cfg.score ?? cfg.fitness;
  if (!fn) throw new Error("SearchConfig missing evaluate/score/fitness");
  return fn;
}

function resolveMutate<T>(cfg: SearchConfig<T>): (c: T, rng: LcgRng, step: number) => T {
  const raw = cfg.mutate ?? cfg.step ?? cfg.perturb;
  if (!raw) throw new Error("SearchConfig missing mutate/step/perturb");

  // Support both calling conventions (candidate-first vs rng-first).
  // For 2-arg mutators: try (c,rng) then fallback (rng,c).
  // For 3-arg mutators: try (c,rng,step) then fallback (rng,c,step).
  return (c: T, rng: LcgRng, step: number) => {
    if (typeof raw !== "function") throw new Error("mutate/step/perturb must be a function");

    if (raw.length <= 2) {
      try {
        return raw(c, rng);
      } catch {
        return raw(rng, c);
      }
    } else {
      try {
        return raw(c, rng, step);
      } catch {
        return raw(rng, c, step);
      }
    }
  };
}

/**
 * Hillclimb local search (deterministic for fixed seed + cfg).
 * Keeps a scalar trace for audit + tests.
 */
export function hillclimb<TCandidate>(cfg: SearchConfig<TCandidate>): SearchResult<TCandidate> {
  const rng = makeLCG(cfg.seed);
  const sample = resolveSample(cfg);
  const evaluate = resolveEval(cfg);
  const mutate = resolveMutate(cfg);

  const step0 = cfg.step0 ?? 1.0;
  const step_decay = cfg.step_decay ?? 0.995;

  let cur = sample(rng);
  let curFit = evaluate(cur);
  let curScalar = primaryScalar(curFit);

  let best = cur;
  let bestFit = curFit;
  let bestScalar = curScalar;

  const traceBestScalar: number[] = [bestScalar];

  let step = step0;
  for (let i = 0; i < cfg.iters; i++) {
    const cand = mutate(cur, rng, step);
    const candFit = evaluate(cand);
    const candScalar = primaryScalar(candFit);

    if (candScalar >= curScalar) {
      cur = cand;
      curFit = candFit;
      curScalar = candScalar;

      if (candScalar >= bestScalar) {
        best = cand;
        bestFit = candFit;
        bestScalar = candScalar;
      }
    }

    traceBestScalar.push(bestScalar);
    step *= step_decay;
  }

  return {
    best,
    bestFitness: bestFit,
    traceBestScalar,
    meta: { seed: cfg.seed, iters: cfg.iters, step0, step_decay },
  };
}

/**
 * Random search baseline (deterministic for fixed seed + cfg).
 */
export function randomSearch<TCandidate>(
  cfg: Omit<SearchConfig<TCandidate>, "mutate" | "step" | "perturb" | "step0" | "step_decay">
): SearchResult<TCandidate> {
  const rng = makeLCG(cfg.seed);
  const sample = resolveSample(cfg as any);
  const evaluate = resolveEval(cfg as any);

  let best = sample(rng);
  let bestFit = evaluate(best);
  let bestScalar = primaryScalar(bestFit);

  const traceBestScalar: number[] = [bestScalar];

  for (let i = 0; i < cfg.iters; i++) {
    const cand = sample(rng);
    const candFit = evaluate(cand);
    const candScalar = primaryScalar(candFit);

    if (candScalar >= bestScalar) {
      best = cand;
      bestFit = candFit;
      bestScalar = candScalar;
    }
    traceBestScalar.push(bestScalar);
  }

  return {
    best,
    bestFitness: bestFit,
    traceBestScalar,
    meta: { seed: cfg.seed, iters: cfg.iters },
  };
}
