export type P20PipelineSpec = {
  schemaVersion: "P20_PIPELINE_SPEC_V0";
  status: "ROADMAP_UNTIL_P16_CALIBRATED_AND_DATA_FROZEN";
  goal: string;
  wiring: {
    p16MetricsContractPath: string;
    p17OutputContractPath: string;
    p18EvalContractPath: string;
    p19RunContractPath: string;
  };
  guardrails: {
    contractOnly: boolean;
    noWetlabClaims: boolean;
    noEditSuccessClaims: boolean;
  };
};

export function getP20PipelineSpec(): P20PipelineSpec {
  return {
    schemaVersion: "P20_PIPELINE_SPEC_V0",
    status: "ROADMAP_UNTIL_P16_CALIBRATED_AND_DATA_FROZEN",
    goal:
      "End-to-end contract wiring check: P17 output -> P18 evaluator stub -> P19 orchestrator stub; metric universe from P16.",
    wiring: {
      p16MetricsContractPath:
        "Glyph_Net_Browser/src/sim/calibration/p16/metrics/p16_metrics_contract.json",
      p17OutputContractPath:
        "Glyph_Net_Browser/src/sim/compiler/p17/p17_recommender_output_contract.json",
      p18EvalContractPath:
        "Glyph_Net_Browser/src/sim/eval/p18/p18_eval_contract.ts",
      p19RunContractPath:
        "Glyph_Net_Browser/src/sim/pipeline/p19/p19_run_contract.ts",
    },
    guardrails: {
      contractOnly: true,
      noWetlabClaims: true,
      noEditSuccessClaims: true,
    },
  };
}
