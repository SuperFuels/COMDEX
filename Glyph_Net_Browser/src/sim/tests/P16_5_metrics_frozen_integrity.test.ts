import { describe, it, expect } from "vitest";
import { loadP16MetricsContract } from "../calibration/p16/metrics/p16_metrics_contract";

describe("P16.5 metrics contract frozen integrity (PILOT)", () => {
  it("requires fully specified units/null/uncertainty/passFailRule", () => {
    const c = loadP16MetricsContract(
      "Glyph_Net_Browser/src/sim/calibration/p16/metrics/p16_metrics_contract.json"
    );
    expect(c.schemaVersion).toBe("P16_METRICS_CONTRACT_V0");
    expect(c.status).toBe("FROZEN_PILOT_V1");
    expect(c.metrics.length).toBeGreaterThanOrEqual(1);

    const m0 = c.metrics[0];
    const mustNotContainTBD = (s: string) => expect(s.includes("TBD")).toBe(false);

    mustNotContainTBD(m0.units);
    mustNotContainTBD(m0.uncertainty);
    mustNotContainTBD(m0.passFailRule);
    mustNotContainTBD(c.nullModelPolicy);
    mustNotContainTBD(c.multipleHypothesisPolicy);
  });
});
