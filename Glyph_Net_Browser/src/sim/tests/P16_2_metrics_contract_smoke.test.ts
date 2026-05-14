import { describe, it, expect } from "vitest";
import { loadP16MetricsContract } from "../calibration/p16/metrics/p16_metrics_contract";

describe("P16.2 metrics contract (ROADMAP)", () => {
  it("parses and exposes required fields", () => {
    const c = loadP16MetricsContract(
      "Glyph_Net_Browser/src/sim/calibration/p16/metrics/p16_metrics_contract.json"
    );
    expect(c.schemaVersion).toBe("P16_METRICS_CONTRACT_V0");
    expect(c.status).toBe("ROADMAP_UNTIL_FROZEN");
    expect(typeof c.nullModelPolicy).toBe("string");
    expect(typeof c.multipleHypothesisPolicy).toBe("string");
    expect(Array.isArray(c.metrics)).toBe(true);
    expect(c.metrics.length).toBeGreaterThanOrEqual(1);
    const m0 = c.metrics[0];
    expect(typeof m0.id).toBe("string");
    expect(typeof m0.passFailRule).toBe("string");
  });
});
