import { getP17RecommenderSpec } from "./p17_recommender_spec";

export type P17EvalWiringContract = {
  schemaVersion: "P17_EVAL_WIRING_V0";
  status: "ROADMAP_UNTIL_P16_CALIBRATED";
  p16: {
    datasetsRegistryPath: string;
    metricsContractPath: string;
  };
  evaluator: {
    kind: "TBD_PROXY_EVAL" | "TBD_CALIBRATED_EVAL";
    notes: string[];
  };
};

export function getP17EvalWiringContract(): P17EvalWiringContract {
  const spec = getP17RecommenderSpec();
  return {
    schemaVersion: "P17_EVAL_WIRING_V0",
    status: "ROADMAP_UNTIL_P16_CALIBRATED",
    p16: {
      datasetsRegistryPath: spec.dependencies.p16DatasetsRegistryPath,
      metricsContractPath: spec.dependencies.p16MetricsContractPath,
    },
    evaluator: {
      kind: "TBD_PROXY_EVAL",
      notes: [
        "ROADMAP: evaluator wiring is contract-only; real evaluator is locked after P16 calibration.",
      ],
    },
  };
}
