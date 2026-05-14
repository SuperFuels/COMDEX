import { describe, expect, test } from "vitest";
import { LcgRng } from "../search/rng_lcg";
import { runGA } from "../search/ga";
import { runES } from "../search/es";

type Genome = number[]; // bitstring

function ones(g: Genome): number {
  return g.reduce((a, b) => a + (b ? 1 : 0), 0);
}

function initGenome(len: number) {
  return (rng: LcgRng): Genome =>
    Array.from({ length: len }, () => (rng.int(0, 1) === 1 ? 1 : 0));
}

function mutateFlipOne(g: Genome, rng: LcgRng): Genome {
  const out = g.slice();
  const i = rng.int(0, out.length - 1);
  out[i] = out[i] ? 0 : 1;
  return out;
}

function crossover1pt(a: Genome, b: Genome, rng: LcgRng): Genome {
  const n = a.length;
  const cut = rng.int(1, n - 1);
  return a.slice(0, cut).concat(b.slice(cut));
}

// Fitness: maximize ones, but add a small penalty if first bit is 1 (toy constraint-ish)
function evalToy(g: Genome) {
  const primary = ones(g);
  const penalty = g[0] === 1 ? 0.25 : 0;
  return { primary: primary - penalty };
}

describe("P14 Search v0.1 (SMOKE)", () => {
  test("GA improves deterministically vs random-ish init (toy objective)", () => {
    const seed = 1337;
    const len = 32;

    const res = runGA<Genome>({
      seed,
      popSize: 24,
      generations: 25,
      init: initGenome(len),
      mutate: mutateFlipOne,
      crossover: crossover1pt,
      evaluate: evalToy,
      tournamentK: 3,
      eliteCount: 2,
    });

    // must be deterministic
    const res2 = runGA<Genome>({
      seed,
      popSize: 24,
      generations: 25,
      init: initGenome(len),
      mutate: mutateFlipOne,
      crossover: crossover1pt,
      evaluate: evalToy,
      tournamentK: 3,
      eliteCount: 2,
    });

    expect(res.bestScalar).toBe(res2.bestScalar);
    expect(res.traceBestScalar).toEqual(res2.traceBestScalar);

    // improvement vs first generation best (trace[0])
    expect(res.traceBestScalar.at(-1)!).toBeGreaterThanOrEqual(res.traceBestScalar[0]);
    // should find something reasonably good
    expect(res.bestFitness.primary).toBeGreaterThan(20);
  });

  test("ES improves deterministically (toy objective)", () => {
    const seed = 4242;
    const len = 32;

    const res = runES<Genome>({
      seed,
      mu: 10,
      lambda: 40,
      generations: 20,
      init: initGenome(len),
      mutate: mutateFlipOne,
      evaluate: evalToy,
      plusStrategy: true,
    });

    const res2 = runES<Genome>({
      seed,
      mu: 10,
      lambda: 40,
      generations: 20,
      init: initGenome(len),
      mutate: mutateFlipOne,
      evaluate: evalToy,
      plusStrategy: true,
    });

    expect(res.bestScalar).toBe(res2.bestScalar);
    expect(res.traceBestScalar).toEqual(res2.traceBestScalar);

    expect(res.traceBestScalar.at(-1)!).toBeGreaterThanOrEqual(res.traceBestScalar[0]);
    expect(res.bestFitness.primary).toBeGreaterThan(20);
  });
});
