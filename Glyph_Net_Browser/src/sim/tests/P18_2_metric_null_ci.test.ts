import { describe, it, expect } from "vitest";
import { evalP18v01 } from "../eval/p18/p18_eval_contract";

describe("P18.2 metric outputs include CI + null model comparison (PILOT)", () => {
  it("emits estimate, CI bounds, nullEstimate, pValue, pass", () => {
    const r = evalP18v01();
    expect(r.results.length).toBeGreaterThanOrEqual(1);

    const x = r.results[0];
    expect(typeof x.metricId).toBe("string");
    expect(typeof x.estimate).toBe("number");
    expect(typeof x.ciLower).toBe("number");
    expect(typeof x.ciUpper).toBe("number");
    expect(typeof x.nullEstimate).toBe("number");
    expect(typeof x.pValue).toBe("number");
    expect(typeof x.pass).toBe("boolean");

    expect(x.ciLower).toBeLessThanOrEqual(x.ciUpper);
    expect(x.pValue).toBeGreaterThan(0);
    expect(x.pValue).toBeLessThanOrEqual(1);
  });
});
