import { describe, it, expect } from "vitest";
import { getP16CalibrationSpec } from "../calibration/p16/p16_calibration_spec";

describe("P16 calibration spec (ROADMAP)", () => {
  it("emits stable contract fields", () => {
    const s = getP16CalibrationSpec();
    expect(s.schemaVersion).toBe("P16_CALIBRATION_SPEC_V0");
    expect(s.status).toBe("ROADMAP_UNTIL_GROUND_TRUTH_FROZEN");
    expect(typeof s.goal).toBe("string");
    expect(typeof s.datasetsRegistryPath).toBe("string");
    expect(typeof s.metricsContractPath).toBe("string");
    expect(s.passFail.requiresNullModel).toBe(true);
    expect(s.passFail.requiresUncertainty).toBe(true);
    expect(s.passFail.requiresMultipleHypothesisPolicy).toBe(true);
  });
});
