import { describe, it, expect } from "vitest";
import { loadP15PredictionRegistry } from "../portability/predictions/p15_predictions";

describe("P15.3 prediction registry (ROADMAP)", () => {
  it("parses and exposes required fields", () => {
    const reg = loadP15PredictionRegistry(
      "Glyph_Net_Browser/src/sim/portability/predictions/p15_predictions.json"
    );

    expect(reg.schemaVersion).toBe("P15_PREDICTIONS_V0");
    expect(reg.status).toBe("ROADMAP_UNTIL_FROZEN");

    expect(Array.isArray(reg.predictions)).toBe(true);
    expect(reg.predictions.length).toBeGreaterThanOrEqual(1);

    const p0 = reg.predictions[0];
    expect(typeof p0.id).toBe("string");
    expect(typeof p0.datasetId).toBe("string");
    expect(typeof p0.preprocessContractId).toBe("string");
    expect(Array.isArray(p0.metrics)).toBe(true);
    expect(Array.isArray(p0.controls.negatives)).toBe(true);
    expect(Array.isArray(p0.controls.ablations)).toBe(true);
    expect(typeof p0.passFailRule).toBe("string");
  });
});
