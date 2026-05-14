import { describe, it, expect } from "vitest";
import fs from "node:fs";
import crypto from "node:crypto";
import { loadP16PreprocessContract } from "../calibration/p16/preprocess/p16_preprocess_contract";

function sha256File(path: string): string {
  const buf = fs.readFileSync(path);
  return crypto.createHash("sha256").update(buf).digest("hex");
}

describe("P16.7 preprocess output sha256 pin (PILOT)", () => {
  it("enforces preprocess output sha256 matches contract", () => {
    const c = loadP16PreprocessContract();
    const p = c.pipelines[0];
    expect(p.outputs.primaryPath).toContain("P16_PILOT_TATA_V1.canon.jsonl");
    expect(p.outputs.sha256).toMatch(/^[a-f0-9]{64}$/);

    const actual = sha256File(p.outputs.primaryPath);
    expect(actual).toBe(p.outputs.sha256);
  });
});
