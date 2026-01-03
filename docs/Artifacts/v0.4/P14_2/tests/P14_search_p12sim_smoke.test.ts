import { describe, expect, it } from "vitest";
import { hillclimb, randomSearch } from "../search/search";
import type { P12A2Intent } from "../search/evaluators/p12_sim";
import { initA2DriveAmp, scoreP12A2, stepA2DriveAmp, scoreToyBits } from "../search/evaluators/p12_sim";

describe("P14 → P12_SIM evaluator wiring (SMOKE)", () => {
  it("hillclimb improves over random baseline deterministically (P12 A2 proxy metrics)", () => {
    const seed = 20260102;

    const resR = randomSearch<P12A2Intent>({
      seed,
      iters: 40,
      init: initA2DriveAmp,
      score: (g) => scoreP12A2(g, seed).fitness,
      bundleMeta: { name: "P14_P12SIM_SMOKE_RANDOM" },
    });

    const resH = hillclimb<P12A2Intent>({
      seed,
      iters: 40,
      init: initA2DriveAmp,
      step: stepA2DriveAmp,
      score: (g) => scoreP12A2(g, seed).fitness,
      bundleMeta: { name: "P14_P12SIM_SMOKE_HILLCLIMB" },
    });

    // deterministic
    const resH2 = hillclimb<P12A2Intent>({
      seed,
      iters: 40,
      init: initA2DriveAmp,
      step: stepA2DriveAmp,
      score: (g) => scoreP12A2(g, seed).fitness,
      bundleMeta: { name: "P14_P12SIM_SMOKE_HILLCLIMB_2" },
    });

    expect(resH.traceBestScalar).toEqual(resH2.traceBestScalar);

    // improvement vs random-ish baseline best
    expect(resH.bestFitness.primary).toBeGreaterThanOrEqual(resR.bestFitness.primary);
    // should end with valid trace
    expect(resH.traceBestScalar.at(-1)!).toBeGreaterThan(0);
  });

  it("toy objective fallback still works", () => {
    const seed = 42;
    type Bits = number[];

    const init = (rng: any): Bits => Array.from({ length: 32 }, () => (rng.int(0, 1) ? 1 : 0));
    const step = (rng: any, g: Bits): Bits => {
      const i = rng.int(0, g.length - 1);
      const out = g.slice();
      out[i] = out[i] ? 0 : 1;
      return out;
    };

    const res = hillclimb<Bits>({
      seed,
      iters: 80,
      init,
      step,
      score: (g) => scoreToyBits(g).fitness,
      bundleMeta: { name: "P14_TOY_FALLBACK" },
    });

    expect(res.bestFitness.primary).toBeGreaterThan(16);
  });
});
