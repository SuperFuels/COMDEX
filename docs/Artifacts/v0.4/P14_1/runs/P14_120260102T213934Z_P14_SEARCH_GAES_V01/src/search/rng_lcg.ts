/**
 * Deterministic RNG (LCG, 32-bit). Exported as a CLASS for "new LcgRng(seed)" callers,
 * plus helper exports for older call sites.
 *
 * Keep this stable; it's part of the audit/repro surface for P14+.
 */
export class LcgRng {
  private state: number;

  constructor(seed: number) {
    this.state = (seed >>> 0) || 0x1;
  }

  /** next uint32 */
  nextU32(): number {
    // Numerical Recipes LCG: x_{n+1} = (1664525 x_n + 1013904223) mod 2^32
    this.state = (Math.imul(1664525, this.state) + 1013904223) >>> 0;
    return this.state;
  }

  /** float in [0,1) */
  nextF01(): number {
    return this.nextU32() / 4294967296;
  }

  /** int in [0, n) */
  nextInt(n: number): number {
    if (!Number.isFinite(n) || n <= 0) throw new Error(`nextInt(n): n must be >0, got ${n}`);
    return Math.floor(this.nextF01() * n);
  }

  /**
   * Back-compat: int(lo, hi) inclusive.
   * Many toy tests use rng.int(0,1) to sample bits.
   */
  int(lo: number, hi: number): number {
    if (!Number.isFinite(lo) || !Number.isFinite(hi)) throw new Error(`int(lo,hi): non-finite`);
    const a = Math.floor(Math.min(lo, hi));
    const b = Math.floor(Math.max(lo, hi));
    const span = b - a + 1;
    if (span <= 0) return a;
    return a + this.nextInt(span);
  }

  /** pick one element uniformly */
  pick<T>(arr: readonly T[]): T {
    if (arr.length === 0) throw new Error("pick: empty array");
    return arr[this.nextInt(arr.length)];
  }

  /** in-place Fisher–Yates shuffle */
  shuffle<T>(arr: T[]): T[] {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = this.nextInt(i + 1);
      const tmp = arr[i];
      arr[i] = arr[j];
      arr[j] = tmp;
    }
    return arr;
  }
}

/** Back-compat helpers (older call sites may import these). */
export function lcgU32(seed: number): number {
  return new LcgRng(seed).nextU32();
}

export function lcgFloat01(seed: number): number {
  return new LcgRng(seed).nextF01();
}
