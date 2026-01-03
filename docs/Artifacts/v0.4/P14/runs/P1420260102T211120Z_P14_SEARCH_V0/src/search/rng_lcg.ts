import type { RNG } from "./types";

/** Tiny deterministic RNG (LCG). Good enough for tests + reproducible search sweeps. */
export function makeLCG(seed: number): RNG {
  let s = seed >>> 0;
  return {
    next() {
      // Numerical Recipes LCG
      s = (Math.imul(1664525, s) + 1013904223) >>> 0;
      return (s >>> 0) / 0x100000000;
    },
    int(maxExclusive: number) {
      return Math.floor(this.next() * maxExclusive);
    },
  };
}
