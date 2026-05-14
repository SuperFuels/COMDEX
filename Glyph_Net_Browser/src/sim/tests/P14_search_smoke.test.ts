import { describe, expect, test } from "vitest";
import { hillclimb, randomSearch } from "../search/search";
import { makeSearchBundle, bundleToStableJson } from "../search/bundle";

type Candidate = { x: number };

function clamp(x: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, x));
}

describe("P14 Search v0 (SMOKE)", () => {
  test("hillclimb improves over random baseline deterministically (toy objective)", () => {
    // Toy objective: hit x=42 with pass if |x-42|<=1.
    // Score is negative distance (higher is better).
    const thresholds = { tol: 1 };

    const evaluate = (c: Candidate) => {
      const dist = Math.abs(c.x - 42);
      return {
        score: -dist,
        pass: dist <= thresholds.tol,
        metrics: { dist },
        thresholds,
      };
    };

    const seed = 1337;

    const rand = randomSearch<Candidate>({
      objective_id: "TOY_HIT_42",
      seed,
      iters: 200,
      sample: (rng) => ({ x: Math.floor(rng.next() * 101) }),
      evaluate,
      stop_when: { pass: true },
    });

    const hc = hillclimb<Candidate>({
      objective_id: "TOY_HIT_42",
      seed,
      iters: 200,
      sample: (rng) => ({ x: Math.floor(rng.next() * 101) }),
      mutate: (rng, cur, step) => {
        // local move in [-step, +step] rounded
        const dx = Math.floor((rng.next() * 2 - 1) * (step * 10));
        return { x: clamp(cur.x + dx, 0, 100) };
      },
      evaluate,
      stop_when: { pass: true },
      step0: 2.0,
      step_decay: 0.98,
    });

    // Determinism check: same seed yields same best in hillclimb.
    const hc2 = hillclimb<Candidate>({
      objective_id: "TOY_HIT_42",
      seed,
      iters: 200,
      sample: (rng) => ({ x: Math.floor(rng.next() * 101) }),
      mutate: (rng, cur, step) => {
        const dx = Math.floor((rng.next() * 2 - 1) * (step * 10));
        return { x: clamp(cur.x + dx, 0, 100) };
      },
      evaluate,
      stop_when: { pass: true },
      step0: 2.0,
      step_decay: 0.98,
    });

    expect(hc.best_fitness.score).toBeGreaterThanOrEqual(rand.best_fitness.score);
    expect(hc.best_fitness.pass).toBe(true);
    expect(hc.best_candidate).toEqual(hc2.best_candidate);
    expect(hc.best_fitness).toEqual(hc2.best_fitness);

    // Bundle is stable except meta.created_utc; we exclude it by fixing the timestamp.
    const created = "2026-01-02T00:00:00Z";
    const b1 = makeSearchBundle({
      objective_id: "TOY_HIT_42",
      seed,
      thresholds,
      result: hc,
      created_utc: created,
      note: "smoke",
    });
    const b2 = makeSearchBundle({
      objective_id: "TOY_HIT_42",
      seed,
      thresholds,
      result: hc2,
      created_utc: created,
      note: "smoke",
    });

    expect(bundleToStableJson(b1)).toEqual(bundleToStableJson(b2));
  });
});
