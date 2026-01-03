import { describe, it, expect } from "vitest";
import { getP15SpecSkeleton } from "../portability/p15_portability_spec";

describe("P15 portability spec skeleton (ROADMAP)", () => {
  it("emits a stable contract shape with at least one prediction", () => {
    const spec = getP15SpecSkeleton();

    expect(spec.status).toBe("ROADMAP_UNTIL_EXTERNAL_ANCHORS");

    expect(typeof spec.mappings.message).toBe("string");
    expect(typeof spec.mappings.key).toBe("string");
    expect(typeof spec.mappings.topology).toBe("string");
    expect(typeof spec.mappings.separation).toBe("string");

    expect(Array.isArray(spec.predictions)).toBe(true);
    expect(spec.predictions.length).toBeGreaterThanOrEqual(1);

    const p0 = spec.predictions[0];
    expect(typeof p0.id).toBe("string");
    expect(typeof p0.dataset.name).toBe("string");
    expect(typeof p0.dataset.version).toBe("string");
    expect(typeof p0.preprocessing.version).toBe("string");
    expect(Array.isArray(p0.metrics)).toBe(true);
    expect(Array.isArray(p0.controls.negatives)).toBe(true);
    expect(Array.isArray(p0.controls.ablations)).toBe(true);
    expect(typeof p0.passFailRule).toBe("string");
  });
});
