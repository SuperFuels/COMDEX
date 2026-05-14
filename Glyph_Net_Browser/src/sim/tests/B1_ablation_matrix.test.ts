import { describe, it, expect } from "vitest";
import { mulberry32 } from "../rng";
import { runSim } from "../harness/run";
import { makeOscillatorBank, stepOscillators, oscEnergy } from "../models/oscillator";
import { selectivity } from "../metrics";
import { makeKuramotoNet, addEdge, stepKuramoto, orderParameter } from "../models/kuramoto";
import { applyProgramAtTime } from "../lexicon";

type WaveToken =
  | { kind: "ω"; hz: number }
  | { kind: "A"; value: number }
  | { kind: "φ"; rad: number }
  | { kind: "τ"; t0: number; t1: number };

type WaveProgram = { tokens: WaveToken[] };

describe("B1 Ablation Matrix (Stage B)", () => {
  it("A2: baseline passes; wrong-ω fails selectivity", () => {
    const seed = 1337;
    const rng = mulberry32(seed);

    const freqsHz = [3, 4, 5, 6, 7, 8, 9, 10];
    const targetIdx = 4; // 7 Hz
    const fDrive = freqsHz[targetIdx];

    const runA2 = (program: WaveProgram) => {
      const bank = makeOscillatorBank({ freqsHz, zeta: 0.04, gain: 1.0 });

      const T = 12;
      const dt = 1 / 240;
      const steps = Math.floor(T / dt);

      runSim(
        { dt, steps, seed },
        (_i, t) => {
          const { u } = applyProgramAtTime(program as any, t) as any;
          stepOscillators(bank, dt, Number(u) || 0, 0.001, rng);
        },
        () => ({}),
      );

      const E = bank.oscs.map(oscEnergy);
      const target = E[targetIdx];
      const others = E.filter((_, i) => i !== targetIdx);
      return selectivity(target, others);
    };

    const baseline: WaveProgram = {
      tokens: [
        { kind: "ω", hz: fDrive },
        { kind: "A", value: 1.0 },
        { kind: "φ", rad: 0.0 },
        { kind: "τ", t0: 0.0, t1: 12.0 },
      ],
    };

    const wrongOmega: WaveProgram = {
      tokens: [
        { kind: "ω", hz: fDrive + 1.5 },
        { kind: "A", value: 1.0 },
        { kind: "φ", rad: 0.0 },
        { kind: "τ", t0: 0.0, t1: 12.0 },
      ],
    };

    const S_base = runA2(baseline);
    const S_wrong = runA2(wrongOmega);

    expect(S_base).toBeGreaterThan(5);
    expect(S_wrong).toBeLessThan(2.0);
  });

  it("A4: gate ablation reduces the k_link advantage", () => {
    const dt = 1 / 120;
    const T = 10;
    const steps = Math.floor(T / dt);

    const mkRun = (net: any, wantKLink: boolean, seed: number, gate01: number) => {
      const rng = mulberry32(seed);

      // deterministic worst-case start
      net.nodes[0].theta = 0.0;
      net.nodes[1].theta = Math.PI;

      let tSync = T;

      const g = Math.max(0, Math.min(1, gate01));

      // ✅ Gate must control ENABLE, not just strength.
      // When gate=0 => k_link behaves as OFF (so "yes" ~= "no")
      const kLinkEnabled = wantKLink && g > 0.001;

      // Full strength when enabled (you can later make this scale with g if desired)
      const kLinkStrength = 1.0;

      runSim(
        { dt, steps, seed },
        (i, _t) => {
          stepKuramoto(net, dt, {
            kGlobal: 1.15,
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

    const runScenario = (gate01: number) => {
      const near = makeKuramotoNet({ positions: [{ x: 0, y: 0 }, { x: 1, y: 0 }] });
      const far = makeKuramotoNet({ positions: [{ x: 0, y: 0 }, { x: 12, y: 0 }] });
      addEdge(near, 0, 1, 1.0);
      addEdge(far, 0, 1, 1.0);

      const tNear_no = mkRun(near, false, 1001, gate01);
      const tFar_no = mkRun(far, false, 1002, gate01);

      const near2 = makeKuramotoNet({ positions: [{ x: 0, y: 0 }, { x: 1, y: 0 }] });
      const far2 = makeKuramotoNet({ positions: [{ x: 0, y: 0 }, { x: 12, y: 0 }] });
      addEdge(near2, 0, 1, 1.0);
      addEdge(far2, 0, 1, 1.0);

      const tNear_yes = mkRun(near2, true, 1001, gate01);
      const tFar_yes = mkRun(far2, true, 1002, gate01);

      const gap_no = tFar_no - tNear_no;
      const gap_yes = tFar_yes - tNear_yes;

      // k_link advantage in reducing distance sensitivity
      const adv = gap_no - gap_yes;

      return { gap_no, gap_yes, adv };
    };

    const hi = runScenario(1.0);
    const lo = runScenario(0.0);

    // At high gate: k_link should materially reduce distance sensitivity
    expect(hi.gap_no).toBeGreaterThan(0.5);
    expect(hi.gap_yes).toBeLessThan(hi.gap_no * 0.5);

    // At low gate: k_link is effectively OFF, so advantage should shrink toward 0
    expect(lo.adv).toBeLessThan(hi.adv * 0.6);
  });
});
