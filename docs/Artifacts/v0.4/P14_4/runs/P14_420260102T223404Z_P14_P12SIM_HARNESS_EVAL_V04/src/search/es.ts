import { LcgRng } from "./rng_lcg";
import type { Fitness } from "./ga";

export type ESOptions<G> = {
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

  mu: number;        // parents
  lambda: number;    // offspring
  generations: number;

  plusStrategy?: boolean; // (mu+lambda) if true else (mu,lambda)
};

export type ESResult<G> = {
  seed: number;
  bestGenome: G;
  bestFitness: { primary: number };
  traceBestScalar: number[];
};

function toPrimary(f: Fitness): number {
  return typeof f === "number" ? f : (f?.primary ?? Number.NEGATIVE_INFINITY);
}

export function runES<G>(opts: ESOptions<G>): ESResult<G> {
  const rng = new LcgRng(opts.seed);

  const init = opts.make ?? opts.init;
  if (!init) throw new Error("ESOptions: missing init/make(rng) initializer");

  const scoreFn = opts.score ?? opts.fitness ?? opts.evaluate;
  if (!scoreFn) throw new Error("ESOptions: missing score/fitness/evaluate(g)");

  const mutate = opts.mutate ?? opts.step ?? opts.perturb;
  if (!mutate) throw new Error("ESOptions: missing mutate/step/perturb(g,rng)");

  const mu = Math.max(1, opts.mu | 0);
  const lambda = Math.max(1, opts.lambda | 0);
  const gens = Math.max(1, opts.generations | 0);
  const plus = opts.plusStrategy ?? true;

  let parents: G[] = Array.from({ length: mu }, () => init(rng));
  let parentScores = parents.map((g) => toPrimary(scoreFn(g)));

  const traceBestScalar: number[] = [];

  for (let gen = 0; gen < gens; gen++) {
    // record current best
    let bestP = 0;
    for (let i = 1; i < parentScores.length; i++) if (parentScores[i] > parentScores[bestP]) bestP = i;
    traceBestScalar.push(parentScores[bestP]);

    // spawn offspring
    const kids: G[] = [];
    for (let i = 0; i < lambda; i++) {
      const p = parents[rng.nextInt(mu)];
      kids.push(mutate(p, rng));
    }
    const kidScores = kids.map((g) => toPrimary(scoreFn(g)));

    // select next parents
    const pool = plus ? parents.concat(kids) : kids;
    const poolScores = plus ? parentScores.concat(kidScores) : kidScores;

    const order = poolScores
      .map((v, i) => ({ v, i }))
      .sort((a, b) => b.v - a.v)
      .slice(0, mu)
      .map((o) => o.i);

    parents = order.map((i) => pool[i]);
    parentScores = order.map((i) => poolScores[i]);
  }

  // final best
  let bestIdx = 0;
  for (let i = 1; i < parentScores.length; i++) if (parentScores[i] > parentScores[bestIdx]) bestIdx = i;

  return {
    seed: opts.seed,
    bestGenome: parents[bestIdx],
    bestFitness: { primary: parentScores[bestIdx] },
    traceBestScalar,
  };
}
