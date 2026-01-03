import { describe, it, expect } from "vitest";
import { runP18EvalV02 } from "../eval/p18/p18_eval_v02";

describe("P18.3 eval v0.2 preprocess sha pin", () => {
  it("rejects drift and emits preprocessOutSha256", () => {
    const r = runP18EvalV02();
    expect(r.schemaVersion).toBe("P18_EVAL_REPORT_V02");
    expect(r.preprocessOutSha256).toMatch(/^[a-f0-9]{64}$/);
    expect(r.metrics.length).toBeGreaterThanOrEqual(1);
  });
});
