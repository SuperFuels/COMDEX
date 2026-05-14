import { describe, it, expect } from "vitest";
import { getP16CalibrationSpec } from "../calibration/p16/p16_calibration_spec";
import { loadP16DatasetRegistry } from "../calibration/p16/datasets/p16_datasets";
import { loadP16MetricsContract } from "../calibration/p16/metrics/p16_metrics_contract";

describe("P16.3 calibration cross-consistency (ROADMAP)", () => {
  it("spec paths resolve and registries are non-empty", () => {
    const spec = getP16CalibrationSpec();
    const d = loadP16DatasetRegistry(spec.datasetsRegistryPath);
    const m = loadP16MetricsContract(spec.metricsContractPath);
    expect(d.datasets.length).toBeGreaterThanOrEqual(1);
    expect(m.metrics.length).toBeGreaterThanOrEqual(1);
  });
});
