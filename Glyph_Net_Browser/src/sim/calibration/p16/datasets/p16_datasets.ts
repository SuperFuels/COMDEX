import fs from "node:fs";

export type P16DatasetRegistry = {
  schemaVersion: "P16_DATASETS_V0";
  status: "ROADMAP_UNTIL_FROZEN" | "FROZEN_PILOT_V1";
  datasets: Array<{
    id: string;
    name: string;
    version: string;
    license: string;
    source: { kind: string; accession: string; url: string };
    files: Array<{ path: string; sha256: string }>;
    notes?: string[];
  }>;
};

export function loadP16DatasetRegistry(path: string): P16DatasetRegistry {
  return JSON.parse(fs.readFileSync(path, "utf8")) as P16DatasetRegistry;
}
