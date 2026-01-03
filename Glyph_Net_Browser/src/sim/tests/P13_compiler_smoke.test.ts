import { describe, it, expect } from "vitest";
import { compileIntent, toCompileBundleJSON } from "../compiler/compile";
import { applyProgramAtTime } from "../lexicon";

describe("P13 Compiler v0 (SMOKE)", () => {
  it("compiles A2 intent into Program(tokens) + deterministic bundle JSON", () => {
    const intent = {
      target: "A2" as const,
      seed: 1337,
      nodeIndex: 4,
      omegaHz: 7,
      amp: 1.0,
      phase: 0.0,
      gate: 1.0,
      note: "smoke",
    };

    const out1 = compileIntent(intent);
    const out2 = compileIntent(intent);

    expect(out1.meta.target).toBe("A2");
    expect(out1.program).toBeTruthy();
    expect(Array.isArray((out1.program as any).tokens)).toBe(true);

    // Executability check: lexicon program application returns an envelope object
    const env = applyProgramAtTime(out1.program as any, 0.5);
    expect(env).toBeTruthy();

    // Deterministic bundle for same intent (created_utc differs)
    const j1 = JSON.parse(toCompileBundleJSON(out1));
    const j2 = JSON.parse(toCompileBundleJSON(out2));
    j1.meta.created_utc = "X";
    j2.meta.created_utc = "X";
    expect(JSON.stringify(j1)).toBe(JSON.stringify(j2));
  });

  it("compiles A3.1 intent into Program(tokens) + thresholds present", () => {
    const intent = {
      target: "A31" as const,
      seed: 4242,
      a: 0,
      b: 1,
      chiralityA: 1 as const,
      chiralityB: -1 as const,
      gate: 1.0,
    };

    const out = compileIntent(intent);
    expect(out.meta.target).toBe("A31");
    expect(Array.isArray((out.program as any).tokens)).toBe(true);
    expect(out.thresholds).toBeTruthy();

    const env = applyProgramAtTime(out.program as any, 0.5);
    expect(env).toBeTruthy();
  });
});
