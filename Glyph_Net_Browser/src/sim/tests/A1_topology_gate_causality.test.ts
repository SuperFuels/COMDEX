import { describe, it, expect } from "vitest";

/**
 * A1 — Topology Gate Causality (Freeze + g sweep)
 * Claim: topo_gate01 is a real control input; Freeze pins topology deterministically.
 * Pass: Freeze cuts topology-change-rate ≥90% AND at least one stability metric is monotonic with g (ρ ≥ 0.7).
 *
 * Implementation hook:
 *  - create module: Glyph_Net_Browser/src/sim/harness/a1_topology_gate.ts
 *  - export: runA1TopologyGateSweep()
 */
type A1Result = {
  topologyChangeRate_noFreeze: number; // e.g. mean edges-changed / step
  topologyChangeRate_freeze: number;
  gSweep: Array<{ g: number; stability: number }>; // monotonic-ish
};

function pearson(xs: number[], ys: number[]): number {
  if (xs.length !== ys.length || xs.length < 2) return 0;
  const n = xs.length;
  const mx = xs.reduce((a, b) => a + b, 0) / n;
  const my = ys.reduce((a, b) => a + b, 0) / n;
  let num = 0, dx = 0, dy = 0;
  for (let i = 0; i < n; i++) {
    const vx = xs[i] - mx;
    const vy = ys[i] - my;
    num += vx * vy;
    dx += vx * vx;
    dy += vy * vy;
  }
  const den = Math.sqrt(dx * dy);
  return den === 0 ? 0 : num / den;
}

describe("A1 — Topology Gate Causality (SIM)", () => {
  it.skip("Freeze cuts topology-change-rate ≥90% and stability is monotonic with g (ρ ≥ 0.7)", async () => {
    // NOTE: flip to `it(...)` when the hook exists.
    const mod = await import("../harness/a1_topology_gate");
    const r = (await mod.runA1TopologyGateSweep()) as A1Result;

    expect(r.topologyChangeRate_noFreeze).toBeGreaterThan(0);
    expect(r.topologyChangeRate_freeze).toBeGreaterThanOrEqual(0);

    const cut = 1 - r.topologyChangeRate_freeze / r.topologyChangeRate_noFreeze;
    expect(cut).toBeGreaterThanOrEqual(0.9);

    expect(r.gSweep.length).toBeGreaterThanOrEqual(5);
    const gs = r.gSweep.map((x) => x.g);
    const st = r.gSweep.map((x) => x.stability);
    const rho = pearson(gs, st);
    expect(rho).toBeGreaterThanOrEqual(0.7);
  });
});
