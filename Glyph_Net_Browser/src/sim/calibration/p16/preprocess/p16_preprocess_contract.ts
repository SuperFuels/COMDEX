import fs from "node:fs";

export type P16PreprocessContract = {
  schemaVersion: "P16_PREPROCESS_CONTRACT_V0";
  status: string;
  pipelines: Array<{
    id: string;
    name: string;
    version: string;
    inputs: { datasetId: string; requiredFiles: string[] };
    steps: string[];
    outputs: { primaryPath: string; sha256: string };
    notes: string[];
  }>;
};

export function loadP16PreprocessContract(
  path = "Glyph_Net_Browser/src/sim/calibration/p16/preprocess/p16_preprocess_contract.json",
): P16PreprocessContract {
  const raw = fs.readFileSync(path, "utf-8");
  return JSON.parse(raw) as P16PreprocessContract;
}
