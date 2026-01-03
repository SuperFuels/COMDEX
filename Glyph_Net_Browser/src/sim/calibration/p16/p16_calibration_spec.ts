export type P16CalibrationSpec = {
  schemaVersion: "P16_CALIBRATION_SPEC_V0";
  status: "ROADMAP_UNTIL_GROUND_TRUTH_FROZEN";
  goal: string;
  datasetsRegistryPath: string;
  metricsContractPath: string;
  passFail: {
    requiresNullModel: boolean;
    requiresUncertainty: boolean;
    requiresMultipleHypothesisPolicy: boolean;
  };
};

export function getP16CalibrationSpec(): P16CalibrationSpec {
  return {
    schemaVersion: "P16_CALIBRATION_SPEC_V0",
    status: "ROADMAP_UNTIL_GROUND_TRUTH_FROZEN",
    goal:
      "Reproduce known regulatory behaviors statistically on frozen public datasets (baseline sanity).",
    datasetsRegistryPath:
      "Glyph_Net_Browser/src/sim/calibration/p16/datasets/p16_datasets.json",
    metricsContractPath:
      "Glyph_Net_Browser/src/sim/calibration/p16/metrics/p16_metrics_contract.json",
    passFail: {
      requiresNullModel: true,
      requiresUncertainty: true,
      requiresMultipleHypothesisPolicy: true,
    },
  };
}
