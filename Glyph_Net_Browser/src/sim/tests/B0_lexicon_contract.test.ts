import { describe, it, expect } from "vitest";
import { TOKEN_SET_V0, applyProgramAtTime } from "../lexicon";

describe("Stage B — Lexicon v0 contract", () => {
  it("token set v0 is locked", () => {
    expect([...TOKEN_SET_V0]).toEqual(["ω", "A", "φ", "p", "m", "τ", "env"]);
  });

  it("applyProgramAtTime respects τ gating and last-wins semantics", () => {
    const prog = {
      name: "contract",
      tokens: [
        { kind: "ω", hz: 2 },
        { kind: "A", value: 1 },
        { kind: "φ", rad: 0 },
        { kind: "τ", t0: 1, t1: 2 },   // only active in [1,2)
        { kind: "A", value: 0.5 },     // last-wins
      ],
    } as const;

    const a0 = applyProgramAtTime(prog, 0.5);
    expect(a0.state.active).toBe(false);
    expect(a0.u).toBe(0);

    const a1 = applyProgramAtTime(prog, 1.25);
    expect(a1.state.active).toBe(true);
    expect(a1.state.omegaHz).toBe(2);
    expect(a1.state.amp).toBe(0.5);
    // u is sin(...) scaled by amp; just ensure nonzero-ish generally
    expect(Math.abs(a1.u)).toBeGreaterThan(0);
  });
});
