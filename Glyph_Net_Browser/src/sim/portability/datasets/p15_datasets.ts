import fs from "node:fs";

export type P15DatasetRegistry = {
  schemaVersion: "P15_DATASETS_V0";
  status: "ROADMAP_UNTIL_FROZEN";
  datasets: Array<{
    id: string;
    name: string;
    version: string;
    license: string;
    source: { kind: string; accession: string; url: string };
    files: Array<{ path: string; sha256: string }>;
    preprocessing: {
      pipelineVersion: string;
      pipelineHash: string;
      determinism: string[];
    };
    notes?: string[];
  }>;
};

export function loadP15DatasetRegistry(path: string): P15DatasetRegistry {
  const raw = fs.readFileSync(path, "utf8");
  return JSON.parse(raw) as P15DatasetRegistry;
}
