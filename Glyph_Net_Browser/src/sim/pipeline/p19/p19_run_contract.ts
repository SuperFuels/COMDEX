import { runP18EvalV02 } from "../../eval/p18/p18_eval_v02";

export type P19RunContractV0 = {
  schemaVersion: "P19_RUN_CONTRACT_V0";
  status: "ROADMAP_UNTIL_P16_CALIBRATED_AND_DATA_FROZEN";

  // legacy wiring surface (tests assert these exact keys)
  inputs: {
    p18EvalContractPath: string;
    p17OutputContractPath: string;
    p16MetricsContractPath: string;
  };

  // informational (not required by older tests, but useful)
  impl: {
    p18EvaluatorModule: string;
  };

  // guardrails (intent)
  contractOnly: true;
  noWetlabClaims: true;
  noEditSuccessClaims: true;
};

export function getP19RunContract(): P19RunContractV0 {
  return {
    schemaVersion: "P19_RUN_CONTRACT_V0",
    status: "ROADMAP_UNTIL_P16_CALIBRATED_AND_DATA_FROZEN",

    inputs: {
      p18EvalContractPath: "Glyph_Net_Browser/src/sim/eval/p18/p18_eval_contract.ts",
      p17OutputContractPath:
        "Glyph_Net_Browser/src/sim/compiler/p17/p17_recommender_output_contract.json",
      p16MetricsContractPath:
        "Glyph_Net_Browser/src/sim/calibration/p16/metrics/p16_metrics_contract.json",
    },

    // legacy: smoke expects c.output.reportSchemaVersion
    output: {
      reportSchemaVersion: "P19_RUN_REPORT_V0",
    },

    // legacy: smoke expects c.guardrails.*
    guardrails: {
      contractOnly: true,
      noWetlabClaims: true,
      noEditSuccessClaims: true,
    },

    // informational (non-asserted by old smokes)
    impl: {
      p18EvaluatorModule: "Glyph_Net_Browser/src/sim/eval/p18/p18_eval_v02.ts",
    },
  };
}

export type P19RunSummary = {
  outputsSeen: number;
  candidatesSeen: number;
  metricIdsReferenced: string[];
};

export type P19RunReportV0 = {
  schemaVersion: "P19_RUN_REPORT_V0";
  status: "ROADMAP_STUB";
  runId: string;
  ranAtUTC: string;

  // legacy nesting (older tests use this)
  summary: P19RunSummary;

  // new top-level aliases (your P20.3 expects this)
  outputsSeen: number;
  candidatesSeen: number;
  metricIdsReferenced: string[];

  // v0.2 additions
  evalSchemaVersion: string;
  preprocessOutSha256: string;
};

export function runP19Stub(): P19RunReportV0 {
  const r18 = runP18EvalV02();
  const now = new Date();
  const metricIds = r18.metrics.map((m) => m.metricId);

  return {
    schemaVersion: "P19_RUN_REPORT_V0",
    status: "ROADMAP_STUB",
    runId: `P19_${now.toISOString()}`,
    ranAtUTC: now.toISOString(),

    summary: {
      outputsSeen: 1,
      candidatesSeen: 1,
      metricIdsReferenced: metricIds,
    },

    // top-level mirrors (for P20.3)
    outputsSeen: 1,
    candidatesSeen: 1,
    metricIdsReferenced: metricIds,

    evalSchemaVersion: r18.schemaVersion,
    preprocessOutSha256: r18.preprocessOutSha256,
  };
}

// compatibility alias
export const runP19 = runP19Stub;
