/**
 * Deterministic RNG (LCG, 32-bit).
 *
 * Exports:
 *  - class LcgRng (for `new LcgRng(seed)`)
 *  - makeLCG(seed) helper (for older call sites expecting a factory)
 *
 * Keep this stable; it's part of the audit/repro surface for P14+.
 */
export interface RngLike {
  u32(): number;
  float01(): number;                  // [0,1)
  int(lo: number, hi: number): number; // inclusive
}

export class LcgRng implements RngLike {
  private state: number;

  constructor(seed: number) {
    this.state = (seed >>> 0) || 0x12345678;
  }

  /** next uint32 */
  u32(): number {
    this.state = (Math.imul(1664525, this.state) + 1013904223) >>> 0;
    return this.state;
  }

  /** uniform in [0,1) */
  float01(): number {
    return this.u32() / 4294967296;
  }

  /** uniform integer in [lo, hi] inclusive */
  int(lo: number, hi: number): number {
    const a = Math.floor(lo);
    const b = Math.floor(hi);
    if (b < a) throw new Error(`int(lo,hi): hi < lo (${b} < ${a})`);
    const span = b - a + 1;
    return a + Math.floor(this.float01() * span);
  }

  pick<T>(arr: readonly T[]): T {
    if (arr.length === 0) throw new Error("pick() on empty array");
    return arr[this.int(0, arr.length - 1)];
  }
}

/** compat factory */
export function makeLCG(seed: number): LcgRng {
  return new LcgRng(seed);
}

/** extra compat alias (harmless) */
export const makeRng = makeLCG;
