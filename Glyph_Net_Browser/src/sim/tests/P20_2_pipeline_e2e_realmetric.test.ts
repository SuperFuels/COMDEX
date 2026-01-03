import { describe, it, expect } from "vitest";
import { runP19Stub } from "../pipeline/p19/p19_run_contract";
import { evalP18v01 } from "../eval/p18/p18_eval_contract";

describe("P20.2 pipeline E2E real-metric smoke (PILOT)", () => {
  it("P19 runs and P18 returns at least one real metric result with CI+null", () => {
    const r19 = runP19Stub();
    expect(r19.schemaVersion).toBe("P19_RUN_REPORT_V0");
    expect(r19.summary.metricIdsReferenced.length).toBeGreaterThanOrEqual(1);

    const r18 = evalP18v01();
    expect(r18.results.length).toBeGreaterThanOrEqual(1);
    const m0 = r18.results[0];
    expect(typeof m0.ciLower).toBe("number");
    expect(typeof m0.ciUpper).toBe("number");
    expect(typeof m0.nullEstimate).toBe("number");
    expect(typeof m0.pValue).toBe("number");
  });
});
