import { describe, it, expect } from "vitest";
import { loadP16PreprocessContract } from "../calibration/p16/preprocess/p16_preprocess_contract";

describe("P16.6 preprocess contract integrity (PILOT)", () => {
  it("exposes a deterministic preprocess pipeline contract surface", () => {
    const c = loadP16PreprocessContract();
    expect(c.schemaVersion).toBe("P16_PREPROCESS_CONTRACT_V0");
    expect(typeof c.status).toBe("string");
    expect(Array.isArray(c.pipelines)).toBe(true);
    expect(c.pipelines.length).toBeGreaterThanOrEqual(1);

    const p = c.pipelines[0];
    expect(typeof p.id).toBe("string");
    expect(typeof p.version).toBe("string");
    expect(typeof p.inputs.datasetId).toBe("string");
    expect(Array.isArray(p.inputs.requiredFiles)).toBe(true);
    expect(p.inputs.requiredFiles.length).toBeGreaterThanOrEqual(1);
    expect(Array.isArray(p.steps)).toBe(true);
    expect(p.steps.length).toBeGreaterThanOrEqual(1);
    expect(typeof p.outputs.primaryPath).toBe("string");
    expect(typeof p.outputs.sha256).toBe("string");
  });
});
