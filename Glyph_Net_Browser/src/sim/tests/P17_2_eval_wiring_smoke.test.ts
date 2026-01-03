import { describe, it, expect } from "vitest";
import { getP17EvalWiringContract } from "../compiler/p17/p17_eval_wiring_contract";

describe("P17.2 eval wiring contract (ROADMAP)", () => {
  it("exposes P16 registry paths and evaluator kind", () => {
    const w = getP17EvalWiringContract();
    expect(w.schemaVersion).toBe("P17_EVAL_WIRING_V0");
    expect(w.status).toBe("ROADMAP_UNTIL_P16_CALIBRATED");
    expect(typeof w.p16.datasetsRegistryPath).toBe("string");
    expect(typeof w.p16.metricsContractPath).toBe("string");
    expect(typeof w.evaluator.kind).toBe("string");
  });
});
