import { describe, it, expect } from "vitest";
import { loadP16DatasetRegistry } from "../calibration/p16/datasets/p16_datasets";

describe("P16.1 dataset registry (ROADMAP)", () => {
  it("parses and exposes required fields", () => {
    const reg = loadP16DatasetRegistry(
      "Glyph_Net_Browser/src/sim/calibration/p16/datasets/p16_datasets.json"
    );
    expect(reg.schemaVersion).toBe("P16_DATASETS_V0");
    expect(reg.status).toBe("ROADMAP_UNTIL_FROZEN");
    expect(Array.isArray(reg.datasets)).toBe(true);
    expect(reg.datasets.length).toBeGreaterThanOrEqual(1);
    const d0 = reg.datasets[0];
    expect(typeof d0.id).toBe("string");
    expect(typeof d0.name).toBe("string");
    expect(typeof d0.version).toBe("string");
    expect(typeof d0.license).toBe("string");
  });
});
