export type Json =
  | null
  | boolean
  | number
  | string
  | Json[]
  | { [k: string]: Json };

export type RNG = {
  /** returns float in [0,1) */
  next(): number;
  /** optional: integer helper */
  int?(maxExclusive: number): number;
};

export type Thresholds = Record<string, number>;

export type Fitness = {
  /** higher is better */
  score: number;
  /** pass/fail under the thresholds declared for this objective */
  pass: boolean;
  /** metrics used to judge (for audit / plotting) */
  metrics: Record<string, number>;
  /** thresholds used (stored in bundle) */
  thresholds: Thresholds;
};

export type SearchBundle<TCandidate extends Json> = {
  schema: "P14_SEARCH_V0";
  objective_id: string;
  seed: number;
  meta: {
    created_utc: string; // allowed to vary; exclude from determinism checks if desired
    note?: string;
  };
  thresholds: Thresholds;
  best: {
    candidate: TCandidate;
    fitness: Fitness;
  };
  history: {
    iters: number;
    best_score_trace: number[];
    best_pass_trace: boolean[];
  };
};

export type SearchConfig<TCandidate> = {
  objective_id: string;

  /** deterministic seed for the RNG supplied by caller */
  seed: number;

  /** total iterations / evaluations */
  iters: number;

  /** how to draw an initial candidate */
  sample(rng: RNG): TCandidate;

  /** how to locally mutate a candidate (hillclimb / ES-style) */
  mutate(rng: RNG, cur: TCandidate, step: number): TCandidate;

  /** evaluate candidate -> fitness (includes thresholds + metrics) */
  evaluate(candidate: TCandidate): Fitness;

  /** optional: stop when pass is achieved and score >= target */
  stop_when?: {
    pass: boolean;
    min_score?: number;
  };

  /** hillclimb step schedule (bigger -> more exploration) */
  step0?: number;
  step_decay?: number; // per-iter multiplicative decay
};

export type SearchResult<TCandidate extends Json> = {
  best_candidate: TCandidate;
  best_fitness: Fitness;
  best_score_trace: number[];
  best_pass_trace: boolean[];
};
