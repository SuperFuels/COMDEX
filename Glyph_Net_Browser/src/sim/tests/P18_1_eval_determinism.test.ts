import { describe, it, expect } from "vitest";
import { evalP18v01 } from "../eval/p18/p18_eval_contract";

describe("P18.1 evaluator determinism (PILOT)", () => {
  it("returns identical metric results across runs (except evaluatedAtUTC)", () => {
    const a = evalP18v01();
    const b = evalP18v01();

    expect(a.schemaVersion).toBe("P18_EVAL_REPORT_V0");
    expect(b.schemaVersion).toBe("P18_EVAL_REPORT_V0");

    // Compare stable fields
    expect(a.status).toBe("PILOT_FROZEN_V1_REALMETRIC");
    expect(b.status).toBe("PILOT_FROZEN_V1_REALMETRIC");

    expect(a.summary).toEqual(b.summary);
    expect(a.results).toEqual(b.results);

    // timestamps can differ
    expect(typeof a.evaluatedAtUTC).toBe("string");
    expect(typeof b.evaluatedAtUTC).toBe("string");
  });
});
