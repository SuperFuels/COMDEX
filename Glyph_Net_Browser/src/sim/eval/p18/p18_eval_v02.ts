import fs from "node:fs";
import crypto from "node:crypto";
import { loadP16PreprocessContract } from "../../calibration/p16/preprocess/p16_preprocess_contract";
import { loadP16MetricsContract } from "../../calibration/p16/metrics/p16_metrics_contract";

export type P18MetricResult = {
  metricId: string;
  datasetId: string;
  value: number;
  ci95: { lo: number; hi: number };
  nullPValue: number;
  pass: boolean;
};

export type P18EvalReportV02 = {
  schemaVersion: "P18_EVAL_REPORT_V02";
  datasetId: string;
  preprocessPipelineId: string;
  preprocessOutSha256: string;
  metrics: P18MetricResult[];
  meta: {
    created_utc: string;
    deterministic: true;
  };
};

const P16_PREPROCESS_CONTRACT_PATH =
  "Glyph_Net_Browser/src/sim/calibration/p16/preprocess/p16_preprocess_contract.json";

const P16_METRICS_CONTRACT_PATH =
  "Glyph_Net_Browser/src/sim/calibration/p16/metrics/p16_metrics_contract.json";

function sha256File(path: string): string {
  const buf = fs.readFileSync(path);
  return crypto.createHash("sha256").update(buf).digest("hex");
}

function readJsonl(path: string): any[] {
  const raw = fs.readFileSync(path, "utf-8").trim();
  if (!raw) return [];
  return raw.split("\n").map((l) => JSON.parse(l));
}

/**
 * v0.2: evaluator reads deterministic preprocess output (sha pinned) then computes 1 metric.
 */
export function runP18EvalV02(): P18EvalReportV02 {
  const pre = loadP16PreprocessContract(P16_PREPROCESS_CONTRACT_PATH);
  const m = loadP16MetricsContract(P16_METRICS_CONTRACT_PATH);

  if (!pre.pipelines?.length) throw new Error("P16 preprocess contract has no pipelines");
  const p = pre.pipelines[0];

  if (!p.outputs?.primaryPath) throw new Error("preprocess pipeline missing outputs.primaryPath");
  if (!p.outputs?.sha256) throw new Error("preprocess pipeline missing outputs.sha256");

  const actualOutSha = sha256File(p.outputs.primaryPath);
  if (actualOutSha !== p.outputs.sha256) {
    throw new Error(`preprocess output sha mismatch: expected ${p.outputs.sha256}, got ${actualOutSha}`);
  }

  const rows = readJsonl(p.outputs.primaryPath);
  if (rows.length < 2) throw new Error("preprocess output too small");

  const hasTata = (s: string) => s.includes("TATA");
  const pos = rows.filter((r) => r.label === "pos");
  const neg = rows.filter((r) => r.label === "neg");

  if (pos.length === 0 || neg.length === 0) throw new Error("missing pos/neg rows");

  const posRate = pos.filter((r) => hasTata(r.sequence)).length / pos.length;
  const negRate = neg.filter((r) => hasTata(r.sequence)).length / neg.length;
  const value = posRate - negRate;

  // pilot v0.2: deterministic fixed-width CI + fixed null p-value (structure locked)
  const ci95 = { lo: Math.max(-1, value - 0.05), hi: Math.min(1, value + 0.05) };
  const nullPValue = 0.01;
  const pass = value > 0;

  const metricId = m.metrics?.[0]?.id ?? "P16_METRIC_PILOT_TATA_DIFF_V1";
  const datasetId = p.inputs.datasetId;

  return {
    schemaVersion: "P18_EVAL_REPORT_V02",
    datasetId,
    preprocessPipelineId: p.id,
    preprocessOutSha256: actualOutSha,
    metrics: [{ metricId, datasetId, value, ci95, nullPValue, pass }],
    meta: { created_utc: new Date().toISOString(), deterministic: true },
  };
}
