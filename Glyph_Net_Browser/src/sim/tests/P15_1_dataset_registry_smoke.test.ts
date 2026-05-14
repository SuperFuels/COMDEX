import { describe, it, expect } from "vitest";
import { loadP15DatasetRegistry } from "../portability/datasets/p15_datasets";

describe("P15.1 dataset registry (ROADMAP)", () => {
  it("parses and exposes required fields", () => {
    const reg = loadP15DatasetRegistry(
      "Glyph_Net_Browser/src/sim/portability/datasets/p15_datasets.json"
    );

    expect(reg.schemaVersion).toBe("P15_DATASETS_V0");
    expect(reg.status).toBe("ROADMAP_UNTIL_FROZEN");

    expect(Array.isArray(reg.datasets)).toBe(true);
    expect(reg.datasets.length).toBeGreaterThanOrEqual(1);

    const d0 = reg.datasets[0];
    expect(typeof d0.id).toBe("string");
    expect(typeof d0.name).toBe("string");
    expect(typeof d0.version).toBe("string");
    expect(typeof d0.license).toBe("string");
    expect(typeof d0.source.kind).toBe("string");
    expect(typeof d0.source.accession).toBe("string");
    expect(typeof d0.source.url).toBe("string");

    expect(Array.isArray(d0.files)).toBe(true);
    expect(typeof d0.preprocessing.pipelineVersion).toBe("string");
    expect(typeof d0.preprocessing.pipelineHash).toBe("string");
    expect(Array.isArray(d0.preprocessing.determinism)).toBe(true);
  });
});
