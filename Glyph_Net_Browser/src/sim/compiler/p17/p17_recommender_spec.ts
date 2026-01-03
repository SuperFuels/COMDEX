export type P17RecommenderSpec = {
  schemaVersion: "P17_RECOMMENDER_SPEC_V0";
  status: "ROADMAP_UNTIL_P16_CALIBRATED";
  goal: string;

  // P17 is explicitly "design recommender (not edits)"
  outputs: {
    candidateMotifs: boolean;
    candidateSchedules: boolean;
    candidateTopologies: boolean;
  };

  // Wiring to calibration contracts (P16) and portability bridge (P15)
  dependencies: {
    p15PortabilityBridge: string; // doc/path ref (roadmap)
    p16DatasetsRegistryPath: string;
    p16MetricsContractPath: string;
  };

  guardrails: {
    noWetlabClaims: boolean;
    noEditSuccessClaims: boolean;
    requiresConfidenceIntervals: boolean;
  };
};

export function getP17RecommenderSpec(): P17RecommenderSpec {
  return {
    schemaVersion: "P17_RECOMMENDER_SPEC_V0",
    status: "ROADMAP_UNTIL_P16_CALIBRATED",
    goal:
      "Given objectives, emit candidate motif/schedule/topology designs + predicted metrics (no edit-success claims).",
    outputs: {
      candidateMotifs: true,
      candidateSchedules: true,
      candidateTopologies: true,
    },
    dependencies: {
      p15PortabilityBridge: "docs/Artifacts/v0.4/P15 (ROADMAP bundle)",
      p16DatasetsRegistryPath:
        "Glyph_Net_Browser/src/sim/calibration/p16/datasets/p16_datasets.json",
      p16MetricsContractPath:
        "Glyph_Net_Browser/src/sim/calibration/p16/metrics/p16_metrics_contract.json",
    },
    guardrails: {
      noWetlabClaims: true,
      noEditSuccessClaims: true,
      requiresConfidenceIntervals: true,
    },
  };
}
