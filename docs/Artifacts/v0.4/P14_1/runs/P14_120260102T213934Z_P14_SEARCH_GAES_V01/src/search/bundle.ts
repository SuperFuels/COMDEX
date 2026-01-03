import type { Json, SearchBundle, SearchResult, Thresholds } from "./types";
import { stableStringify } from "./stable_json";

export function makeSearchBundle<TCandidate extends Json>(args: {
  objective_id: string;
  seed: number;
  thresholds: Thresholds;
  result: SearchResult<TCandidate>;
  created_utc: string;
  note?: string;
}): SearchBundle<TCandidate> {
  return {
    schema: "P14_SEARCH_V0",
    objective_id: args.objective_id,
    seed: args.seed,
    meta: { created_utc: args.created_utc, note: args.note },
    thresholds: args.thresholds,
    best: {
      candidate: args.result.best_candidate,
      fitness: args.result.best_fitness,
    },
    history: {
      iters: args.result.best_score_trace.length,
      best_score_trace: args.result.best_score_trace,
      best_pass_trace: args.result.best_pass_trace,
    },
  };
}

/** Deterministic JSON (key-sorted) for audit bundles. */
export function bundleToStableJson(bundle: SearchBundle<Json>): string {
  return stableStringify(bundle);
}
