import { describe, it, expect } from "vitest";
import { evalP18Stub } from "../eval/p18/p18_eval_contract";

describe("P18 eval report (ROADMAP)", () => {
  it("runs stub evaluator and returns a report", () => {
    const r = evalP18Stub();
    expect(r.schemaVersion).toBe("P18_EVAL_REPORT_V0");
    expect(r.status).toBe("ROADMAP_STUB");
    expect(typeof r.evaluatedAtUTC).toBe("string");
    expect(r.summary.outputsSeen).toBeGreaterThanOrEqual(1);
    expect(r.summary.candidatesSeen).toBeGreaterThanOrEqual(1);
    expect(Array.isArray(r.summary.metricIdsReferenced)).toBe(true);
  });
});
