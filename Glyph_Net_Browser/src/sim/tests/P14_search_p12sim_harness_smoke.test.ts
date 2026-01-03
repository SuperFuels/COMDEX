import { describe, expect, it } from "vitest";
import { hillclimb, randomSearch } from "../search/search";
import { initA2DriveAmp, stepA2DriveAmp, scoreP12A2Harness } from "../search/evaluators/p12_harness";

describe("P14_4 → P12_SIM harness evaluator (SMOKE)", () => {
  it("hillclimb improves over random baseline deterministically (P12 harness A2 metrics)", () => {
    const seed = 24681357;

    const cfg = {
      seed,
      iters: 120,
      sample: (rng: any) => initA2DriveAmp(rng),
      mutate: (rng: any, cur: any, _step: number) => stepA2DriveAmp(rng, cur),
      evaluate: (c: any) => scoreP12A2Harness(c, 1337).fitness,
    };

    const rand = randomSearch(cfg as any);
    const hc = hillclimb(cfg as any);
    const hc2 = hillclimb(cfg as any);

    // determinism
    expect(hc.traceBestScalar).toEqual(hc2.traceBestScalar);
    expect(hc.best_candidate ?? hc.best).toEqual(hc2.best_candidate ?? hc2.best);

    // improvement vs baseline
    const randLast = rand.traceBestScalar.at(-1)!;
    const hcLast = hc.traceBestScalar.at(-1)!;
    expect(hcLast).toBeGreaterThanOrEqual(randLast);

    // assert we really used harness (not proxy)
    const best = (hc.best_candidate ?? hc.best) as any;
    const { diag } = scoreP12A2Harness(best, 1337);
    expect(diag.source).toBe("P12_SIM");
  });
});
