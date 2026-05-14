import fs from "node:fs";

export type P15PredictionRegistry = {
  schemaVersion: "P15_PREDICTIONS_V0";
  status: "ROADMAP_UNTIL_FROZEN";
  predictions: Array<{
    id: string;
    datasetId: string;
    preprocessContractId: string;
    metrics: Array<{ name: string; expected: string; tolerance?: string }>;
    controls: { negatives: string[]; ablations: string[] };
    passFailRule: string;
    notes?: string[];
  }>;
};

export function loadP15PredictionRegistry(path: string): P15PredictionRegistry {
  const raw = fs.readFileSync(path, "utf8");
  return JSON.parse(raw) as P15PredictionRegistry;
}
