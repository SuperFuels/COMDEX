import { describe, it, expect } from "vitest";
import { runP19Stub } from "../pipeline/p19/p19_run_contract";

describe("P20.3 pipeline E2E uses preprocess sha (v0.2)", () => {
  it("emits preprocessOutSha256 and a v0.2 eval schema", () => {
    const r = runP19Stub();
    expect(r.schemaVersion).toBe("P19_RUN_REPORT_V0");
    expect(r.evalSchemaVersion).toBe("P18_EVAL_REPORT_V02");
    expect(r.preprocessOutSha256).toMatch(/^[a-f0-9]{64}$/);
    expect(r.metricIdsReferenced.length).toBeGreaterThanOrEqual(1);
  });
});
