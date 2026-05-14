import fs from "node:fs";

export type P15PreprocessContract = {
  schemaVersion: "P15_PREPROCESS_CONTRACT_V0";
  status: "ROADMAP_UNTIL_FROZEN";
  id: string;

  pipelineVersion: string;
  pipelineHash: string;
  determinism: string[];

  inputs: Array<{ id: string; kind: string; notes?: string[] }>;
  outputs: Array<{ id: string; kind: string; notes?: string[] }>;
  notes?: string[];
};

export function loadP15PreprocessContract(path: string): P15PreprocessContract {
  const raw = fs.readFileSync(path, "utf8");
  return JSON.parse(raw) as P15PreprocessContract;
}
