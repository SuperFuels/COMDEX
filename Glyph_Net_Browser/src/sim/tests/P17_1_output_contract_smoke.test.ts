import { describe, it, expect } from "vitest";
import { loadP17OutputContract } from "../compiler/p17/p17_recommender_output_contract";

describe("P17.1 output contract (ROADMAP)", () => {
  it("parses and exposes required fields", () => {
    const c = loadP17OutputContract(
      "Glyph_Net_Browser/src/sim/compiler/p17/p17_recommender_output_contract.json"
    );
    expect(c.schemaVersion).toBe("P17_OUTPUT_CONTRACT_V0");
    expect(c.status).toBe("ROADMAP_UNTIL_EVALUATOR_LOCKED");
    expect(Array.isArray(c.outputs)).toBe(true);
    expect(c.outputs.length).toBeGreaterThanOrEqual(1);

    const o0 = c.outputs[0];
    expect(typeof o0.id).toBe("string");
    expect(Array.isArray(o0.candidates)).toBe(true);
    expect(Array.isArray(o0.traceBestScalar)).toBe(true);

    const cand0 = o0.candidates[0];
    expect(typeof cand0.candidateId).toBe("string");
    expect(Array.isArray(cand0.predictions)).toBe(true);

    const p0 = cand0.predictions[0];
    expect(typeof p0.metricId).toBe("string");
    expect(typeof p0.confidence).toBe("number");
  });
});
