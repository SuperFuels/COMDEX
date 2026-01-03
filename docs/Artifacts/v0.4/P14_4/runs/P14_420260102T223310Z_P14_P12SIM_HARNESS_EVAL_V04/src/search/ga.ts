import { LcgRng } from "./rng_lcg";

export type Fitness = number | { primary: number; [k: string]: any };

export type GAOptions<G> = {
  seed: number;

  // init (compat)
  init?: (rng: LcgRng) => G;
  make?: (rng: LcgRng) => G;

  // score (compat)
  score?: (g: G) => Fitness;
  fitness?: (g: G) => Fitness;
  evaluate?: (g: G) => Fitness;

  // mutate (compat)
  mutate?: (g: G, rng: LcgRng) => G;
  step?: (g: G, rng: LcgRng) => G;
  perturb?: (g: G, rng: LcgRng) => G;

  // crossover (optional)
  crossover?: (a: G, b: G, rng: LcgRng) => G;

  popSize: number;
  generations: number;

  eliteCount?: number;
  tournamentK?: number;
};

export type GAResult<G> = {
  seed: number;
  bestGenome: G;
  bestFitness: { primary: number };
  traceBestScalar: number[];
};

function toPrimary(f: Fitness): number {
  return typeof f === "number" ? f : (f?.primary ?? Number.NEGATIVE_INFINITY);
}

export function runGA<G>(opts: GAOptions<G>): GAResult<G> {
  const rng = new LcgRng(opts.seed);

  const init = opts.make ?? opts.init;
  if (!init) throw new Error("GAOptions: missing init/make(rng) initializer");

  const scoreFn = opts.score ?? opts.fitness ?? opts.evaluate;
  if (!scoreFn) throw new Error("GAOptions: missing score/fitness/evaluate(g)");

  const mutate = opts.mutate ?? opts.step ?? opts.perturb;
  if (!mutate) throw new Error("GAOptions: missing mutate/step/perturb(g,rng)");

  const popSize = Math.max(2, opts.popSize | 0);
  const gens = Math.max(1, opts.generations | 0);
  const k = Math.max(2, opts.tournamentK ?? 3);
  const elite = Math.max(0, Math.min(popSize, opts.eliteCount ?? 1));

  // init population
  let pop: G[] = Array.from({ length: popSize }, () => init(rng));
  let scores: number[] = pop.map((g) => toPrimary(scoreFn(g)));

  const traceBestScalar: number[] = [];

  function argmax(xs: number[]): number {
    let bi = 0;
    let bv = xs[0] ?? Number.NEGATIVE_INFINITY;
    for (let i = 1; i < xs.length; i++) {
      if (xs[i] > bv) {
        bv = xs[i];
        bi = i;
      }
    }
    return bi;
  }

  function tournamentPick(): G {
    let bestIdx = rng.nextInt(popSize);
    let bestVal = scores[bestIdx];
    for (let i = 1; i < k; i++) {
      const j = rng.nextInt(popSize);
      const v = scores[j];
      if (v > bestVal) {
        bestVal = v;
        bestIdx = j;
      }
    }
    return pop[bestIdx];
  }

  for (let gen = 0; gen < gens; gen++) {
    // record best for this generation
    const bi = argmax(scores);
    traceBestScalar.push(scores[bi]);

    // elitism
    const idxSorted = scores
      .map((v, i) => ({ v, i }))
      .sort((a, b) => b.v - a.v)
      .map((o) => o.i);

    const nextPop: G[] = [];
    for (let e = 0; e < elite; e++) nextPop.push(pop[idxSorted[e]]);

    // fill remainder
    while (nextPop.length < popSize) {
      const p1 = tournamentPick();
      const child = opts.crossover ? opts.crossover(p1, tournamentPick(), rng) : p1;
      nextPop.push(mutate(child, rng));
    }

    pop = nextPop;
    scores = pop.map((g) => toPrimary(scoreFn(g)));
  }

  // final best
  let bestIdx = 0;
  for (let i = 1; i < scores.length; i++) if (scores[i] > scores[bestIdx]) bestIdx = i;

  return {
    seed: opts.seed,
    bestGenome: pop[bestIdx],
    bestFitness: { primary: scores[bestIdx] },
    traceBestScalar,
  };
}
