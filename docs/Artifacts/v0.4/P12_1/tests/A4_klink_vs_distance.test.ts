import { describe, it, expect } from "vitest";
import { mulberry32 } from "../rng";
import { runSim } from "../harness/run";
import { makeKuramotoNet, addEdge, stepKuramoto, orderParameter } from "../models/kuramoto";

describe("A4 k_link vs distance (SIM)", () => {
  it("k_link makes convergence less sensitive to distance (optionally gated)", () => {
    const dt = 1 / 120;
    const T = 10;
    const steps = Math.floor(T / dt);

    const mkRun = (net: any, kLinkEnabled: boolean, seed: number, gate01: number) => {
      const rng = mulberry32(seed);

      // deterministic worst-case start: maximally out of phase
      net.nodes[0].theta = 0.0;
      net.nodes[1].theta = Math.PI;

      let tSync = T;

      const g = Math.max(0, Math.min(1, gate01));
      const kGlobal = 1.15; // keep baseline identical
      const kLinkStrength = 1.0 * (0.20 + 0.80 * g); // only k_link is gated

      runSim(
        { dt, steps, seed },
        (i, _t) => {
          stepKuramoto(net, dt, {
            kGlobal,
            distScale: 3.0,
            noiseStd: 0.008,
            rng,
            kLinkEnabled,
            kLinkPairs: [[0, 1]],
            kLinkStrength,
          });

          const R = orderParameter(net);
          if (R >= 0.92 && tSync === T) tSync = i * dt;
        },
        () => ({ tSync }),
      );

      return tSync;
    };

    // Without k_link
    const near = makeKuramotoNet({ positions: [{ x: 0, y: 0 }, { x: 1, y: 0 }] });
    const far = makeKuramotoNet({ positions: [{ x: 0, y: 0 }, { x: 12, y: 0 }] });
    addEdge(near, 0, 1, 1.0);
    addEdge(far, 0, 1, 1.0);

    const tNear_no = mkRun(near, false, 1001, 1.0);
    const tFar_no = mkRun(far, false, 1002, 1.0);

    // With k_link (gate high)
    const near2 = makeKuramotoNet({ positions: [{ x: 0, y: 0 }, { x: 1, y: 0 }] });
    const far2 = makeKuramotoNet({ positions: [{ x: 0, y: 0 }, { x: 12, y: 0 }] });
    addEdge(near2, 0, 1, 1.0);
    addEdge(far2, 0, 1, 1.0);

    const tNear_yes = mkRun(near2, true, 1001, 1.0);
    const tFar_yes = mkRun(far2, true, 1002, 1.0);

    const gap_no = tFar_no - tNear_no;
    const gap_yes = tFar_yes - tNear_yes;

    expect(gap_no).toBeGreaterThan(0.5);
    expect(gap_yes).toBeLessThan(gap_no * 0.5);
  });
});
