import { describe, it, expect } from "vitest";
import { getP17RecommenderSpec } from "../compiler/p17/p17_recommender_spec";
import { loadP16DatasetRegistry } from "../calibration/p16/datasets/p16_datasets";
import { loadP16MetricsContract } from "../calibration/p16/metrics/p16_metrics_contract";

describe("P17.3 cross-link to P16 calibration contracts (ROADMAP)", () => {
  it("loads P16 registries via P17 spec wiring and checks referenced metric ids exist", () => {
    const spec = getP17RecommenderSpec();

    const d = loadP16DatasetRegistry(spec.dependencies.p16DatasetsRegistryPath);
    const m = loadP16MetricsContract(spec.dependencies.p16MetricsContractPath);

    expect(d.datasets.length).toBeGreaterThanOrEqual(1);
    expect(m.metrics.length).toBeGreaterThanOrEqual(1);

    const metricIds = new Set(m.metrics.map((x) => x.id));
    // The placeholder output contract references this metric id.
    expect(metricIds.has("KNOWN_EFFECT_REPRODUCTION")).toBe(true);
  });
});
