import fs from "node:fs";

export type P16MetricsContract = {
  schemaVersion: "P16_METRICS_CONTRACT_V0";
  status: "ROADMAP_UNTIL_FROZEN" | "FROZEN_PILOT_V1";
  nullModelPolicy: string;
  multipleHypothesisPolicy: string;
  metrics: Array<{
    id: string;
    name: string;
    expected: string;
    units: string;
    uncertainty: string;
    passFailRule: string;
  }>;
};

export function loadP16MetricsContract(path: string): P16MetricsContract {
  return JSON.parse(fs.readFileSync(path, "utf8")) as P16MetricsContract;
}
