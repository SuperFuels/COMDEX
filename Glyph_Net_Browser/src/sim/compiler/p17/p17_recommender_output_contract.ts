import fs from "node:fs";

export type P17RecommenderOutputContract = {
  schemaVersion: "P17_OUTPUT_CONTRACT_V0";
  status: "ROADMAP_UNTIL_EVALUATOR_LOCKED";
  outputs: Array<{
    id: string;
    candidates: Array<{
      candidateId: string;
      motif: string;
      schedule: string;
      topology: string;
      predictions: Array<{
        metricId: string;
        predicted: string;
        uncertainty: string;
        confidence: number;
      }>;
      notes?: string[];
    }>;
    traceBestScalar: number[];
  }>;
};

export function loadP17OutputContract(path: string): P17RecommenderOutputContract {
  return JSON.parse(fs.readFileSync(path, "utf8")) as P17RecommenderOutputContract;
}
