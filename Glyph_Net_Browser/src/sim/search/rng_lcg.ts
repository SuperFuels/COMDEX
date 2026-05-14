/**
 * Deterministic RNG (LCG, 32-bit).
 *
 * Exports:
 *  - class LcgRng (for `new LcgRng(seed)`)
 *  - makeLCG(seed) helper (older call sites expecting a factory)
 *
 * Compatibility surface (DO NOT BREAK):
 *  - next(): number          // alias of float01()
 *  - nextInt(n): number      // integer in [0,n)
 *  - int(lo,hi): number      // integer in [lo,hi] inclusive
 *  - float01(): number       // [0,1)
 */
export interface RngLike {
  u32(): number;
  float01(): number;
  next(): number;
  nextInt(n: number): number;
  int(lo: number, hi: number): number;
}

export class LcgRng implements RngLike {
  private state: number;

  constructor(seed: number) {
    this.state = (seed >>> 0) || 0x12345678;
  }

  u32(): number {
    this.state = (Math.imul(1664525, this.state) + 1013904223) >>> 0;
    return this.state;
  }

  float01(): number {
    return this.u32() / 4294967296;
  }

  next(): number {
    return this.float01();
  }

  nextInt(n: number): number {
    const nn = Math.floor(n);
    if (nn <= 0) throw new Error(`nextInt(n): n must be > 0 (got ${n})`);
    return Math.floor(this.float01() * nn);
  }

  int(lo: number, hi: number): number {
    const a = Math.floor(lo);
    const b = Math.floor(hi);
    if (b < a) throw new Error(`int(lo,hi): hi < lo (${b} < ${a})`);
    const span = b - a + 1;
    return a + this.nextInt(span);
  }

  pick<T>(arr: readonly T[]): T {
    if (arr.length === 0) throw new Error("pick() on empty array");
    return arr[this.nextInt(arr.length)];
  }
}

export function makeLCG(seed: number): LcgRng {
  return new LcgRng(seed);
}

export const makeRng = makeLCG;
