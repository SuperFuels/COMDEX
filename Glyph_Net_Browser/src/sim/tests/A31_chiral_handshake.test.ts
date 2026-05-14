import { describe, it, expect } from "vitest";
import { mulberry32 } from "../rng";
import { runSim } from "../harness/run";
import { makeKuramotoNet, addEdge, stepKuramoto } from "../models/kuramoto";

function mean(xs: number[]) {
  return xs.reduce((a, b) => a + b, 0) / Math.max(1, xs.length);
}
function std(xs: number[]) {
  if (xs.length <= 1) return 0;
  const m = mean(xs);
  const v = mean(xs.map((x) => (x - m) * (x - m)));
  return Math.sqrt(v);
}

function wrapPi(x: number) {
  // map to (-pi, pi]
  const twopi = 2 * Math.PI;
  x = ((x + Math.PI) % twopi + twopi) % twopi - Math.PI;
  return x;
}

function linearSlope(ts: number[], ys: number[]) {
  // least-squares slope
  const n = Math.min(ts.length, ys.length);
  if (n <= 1) return 0;

  let tMean = 0, yMean = 0;
  for (let i = 0; i < n; i++) {
    tMean += ts[i];
    yMean += ys[i];
  }
  tMean /= n;
  yMean /= n;

  let num = 0, den = 0;
  for (let i = 0; i < n; i++) {
    const dt = ts[i] - tMean;
    const dy = ys[i] - yMean;
    num += dt * dy;
    den += dt * dt;
  }
  return den > 0 ? num / den : 0;
}

type RunOut = {
  drift: number; // |d/dt Δθ| over last window (rad/s)
  C: number;     // coupling proxy in [0,1] (higher = more locked)
};

/**
 * A3.1 — Chiral Handshake (SIM)
 *
 * Protocol claim:
 *  - CH match => coupling enabled => phase-lock (Δθ drift -> 0)
 *  - CH mismatch => coupling suppressed => phase drifts ~ Δω (no lock)
 *
 * IMPORTANT: For 2 nodes, Kuramoto order parameter R can spike near 1 even without coupling.
 * So we measure *phase-lock* directly via Δθ drift over a tail window.
 */
describe("A3.1 Chiral Handshake (SIM)", () => {
  it("matched chirality yields stronger coupling than mismatched (ΔC > 3σ)", () => {
    const dt = 1 / 240;
    const T = 12;
    const steps = Math.floor(T / dt);

    // tail window for drift measurement
    const tailSec = 3.0;
    const tailSteps = Math.floor(tailSec / dt);

    // Plant difficulty knobs:
    // - small but non-trivial detuning so mismatch won’t “accidentally align”
    // - distance where coupling matters but match can still lock
    const distance = 2.0;

    const runOne = (seed: number, match: boolean): RunOut => {
      const rng = mulberry32(seed);

      // two nodes separated by "distance"
      const net = makeKuramotoNet({
        positions: [
          { x: 0, y: 0 },
          { x: distance, y: 0 },
        ],
        wHz: 1.0,
        wJitterHz: 0.05, // Δf = 0.10 Hz -> Δω ~ 0.628 rad/s
      });

      // base edge
      addEdge(net, 0, 1, 1.0);

      // seeded initial phases
      net.nodes[0].theta = (rng() * 2 - 1) * Math.PI;
      net.nodes[1].theta = (rng() * 2 - 1) * Math.PI;

      // protocol gate (handshake)
      const handshakeGain = match ? 1.0 : 0.01;
      net.edges[0].k *= handshakeGain;

      // track unwrapped Δθ(t) so drift is measurable
      const ts: number[] = [];
      const dthetaUnwrapped: number[] = [];

      let prev = wrapPi(net.nodes[1].theta - net.nodes[0].theta);
      let unwrapped = prev;

      runSim(
        { dt, steps, seed },
        (i, t) => {
          stepKuramoto(net, dt, {
            kGlobal: 2.2,
            distScale: 3.0,
            noiseStd: 0.006,
            rng,
            kLinkEnabled: false,
            kLinkPairs: [],
            kLinkStrength: 1.0,
          });

          // update Δθ unwrapped
          const cur = wrapPi(net.nodes[1].theta - net.nodes[0].theta);
          const stepDiff = wrapPi(cur - prev); // shortest diff
          unwrapped += stepDiff;
          prev = cur;

          // keep only tail window samples to compute drift
          if (i >= steps - tailSteps) {
            ts.push(t);
            dthetaUnwrapped.push(unwrapped);
          }
        },
        () => null,
      );

      const slope = Math.abs(linearSlope(ts, dthetaUnwrapped)); // rad/s

      // coupling proxy: 1 when slope≈0, 0 when slope≈Δω-ish
      // Use Δω_ref ~ 0.7 rad/s for normalization (close to expected free drift here).
      const C = Math.max(0, Math.min(1, 1 - slope / 0.7));

      return { drift: slope, C };
    };

    const seeds = [101, 202, 303, 404, 505, 606, 707, 808];

    const matchRuns = seeds.map((s) => runOne(s, true));
    const mismatchRuns = seeds.map((s) => runOne(s, false));

    const Cm = matchRuns.map((r) => r.C);
    const Cu = mismatchRuns.map((r) => r.C);

    const mMatch = mean(Cm);
    const mMis = mean(Cu);
    const sMatch = std(Cm);
    const sMis = std(Cu);

    const dC = mMatch - mMis;
    const sigma = Math.max(1e-9, Math.max(sMatch, sMis));

    // sanity: match should lock (low drift), mismatch should drift
    const driftMatch = mean(matchRuns.map((r) => r.drift));
    const driftMis = mean(mismatchRuns.map((r) => r.drift));

    expect(driftMatch).toBeLessThan(0.08);  // locked: near-flat Δθ
    expect(driftMis).toBeGreaterThan(0.20); // unlocked: drifting Δθ

    // coupling proxy separation
    expect(mMatch).toBeGreaterThan(0.55);
    expect(mMis).toBeLessThan(0.35);

    // protocol separation (3σ-style)
    expect(dC).toBeGreaterThan(3.0 * sigma);
  });
});
