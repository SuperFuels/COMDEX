import { describe, it, expect } from "vitest";
import { runP19Stub } from "../pipeline/p19/p19_run_contract";

describe("P19 run stub (ROADMAP)", () => {
  it("runs and returns a report with embedded summary", () => {
    const r = runP19Stub();
    expect(r.schemaVersion).toBe("P19_RUN_REPORT_V0");
    expect(r.status).toBe("ROADMAP_STUB");
    expect(typeof r.runId).toBe("string");
    expect(typeof r.ranAtUTC).toBe("string");

    expect(r.summary.outputsSeen).toBeGreaterThanOrEqual(1);
    expect(r.summary.candidatesSeen).toBeGreaterThanOrEqual(1);
    expect(Array.isArray(r.summary.metricIdsReferenced)).toBe(true);
    expect(r.summary.metricIdsReferenced.length).toBeGreaterThanOrEqual(1);
  });
});
