import type { Json, SearchConfig, SearchResult } from "./types";
import { makeLCG } from "./rng_lcg";

/**
 * P14 search v0: deterministic hillclimb seeded with one random sample + local mutations.
 * - Evaluator is injected (so you can plug in SIM harness / compiler evaluation later).
 * - Stores best-score trace for audit.
 */
export function hillclimb<TCandidate extends Json>(
  cfg: SearchConfig<TCandidate>
): SearchResult<TCandidate> {
  const rng = makeLCG(cfg.seed);

  const step0 = cfg.step0 ?? 1.0;
  const step_decay = cfg.step_decay ?? 0.995;

  let cur = cfg.sample(rng);
  let curFit = cfg.evaluate(cur);

  let best = cur;
  let bestFit = curFit;

  const best_score_trace: number[] = [];
  const best_pass_trace: boolean[] = [];

  let step = step0;

  for (let it = 0; it < cfg.iters; it++) {
    // propose mutation from current
    const cand = cfg.mutate(rng, cur, step);
    const fit = cfg.evaluate(cand);

    // greedy accept if improves score OR flips to pass with comparable score
    const better =
      fit.score > curFit.score ||
      (fit.pass && !curFit.pass && fit.score >= curFit.score - 1e-12);

    if (better) {
      cur = cand;
      curFit = fit;
    }

    if (
      curFit.score > bestFit.score ||
      (curFit.pass && !bestFit.pass && curFit.score >= bestFit.score - 1e-12)
    ) {
      best = cur;
      bestFit = curFit;
    }

    best_score_trace.push(bestFit.score);
    best_pass_trace.push(bestFit.pass);

    if (cfg.stop_when?.pass && bestFit.pass) {
      if (cfg.stop_when.min_score == null || bestFit.score >= cfg.stop_when.min_score) break;
    }

    step *= step_decay;
  }

  return { best_candidate: best, best_fitness: bestFit, best_score_trace, best_pass_trace };
}

/**
 * Baseline: random search (pure sampling).
 */
export function randomSearch<TCandidate extends Json>(
  cfg: Omit<SearchConfig<TCandidate>, "mutate" | "step0" | "step_decay">
): SearchResult<TCandidate> {
  const rng = makeLCG(cfg.seed);

  let best = cfg.sample(rng);
  let bestFit = cfg.evaluate(best);

  const best_score_trace: number[] = [];
  const best_pass_trace: boolean[] = [];

  for (let it = 0; it < cfg.iters; it++) {
    const cand = cfg.sample(rng);
    const fit = cfg.evaluate(cand);

    if (
      fit.score > bestFit.score ||
      (fit.pass && !bestFit.pass && fit.score >= bestFit.score - 1e-12)
    ) {
      best = cand;
      bestFit = fit;
    }

    best_score_trace.push(bestFit.score);
    best_pass_trace.push(bestFit.pass);

    if (cfg.stop_when?.pass && bestFit.pass) {
      if (cfg.stop_when.min_score == null || bestFit.score >= cfg.stop_when.min_score) break;
    }
  }

  return { best_candidate: best, best_fitness: bestFit, best_score_trace, best_pass_trace };
}

export * from "./fitness";
export * from "./ga";
export * from "./es";
