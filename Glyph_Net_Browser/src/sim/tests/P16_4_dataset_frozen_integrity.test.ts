import { describe, it, expect } from "vitest";
import fs from "node:fs";
import crypto from "node:crypto";
import { loadP16DatasetRegistry } from "../calibration/p16/datasets/p16_datasets";

function sha256File(path: string): string {
  const buf = fs.readFileSync(path);
  return crypto.createHash("sha256").update(buf).digest("hex");
}

describe("P16.4 dataset registry frozen integrity (PILOT)", () => {
  it("requires accession/license/files and enforces sha256", () => {
    const reg = loadP16DatasetRegistry(
      "Glyph_Net_Browser/src/sim/calibration/p16/datasets/p16_datasets.json"
    );
    expect(reg.schemaVersion).toBe("P16_DATASETS_V0");
    expect(reg.status).toBe("FROZEN_PILOT_V1");
    expect(reg.datasets.length).toBeGreaterThanOrEqual(1);

    const ds = reg.datasets[0];
    expect(typeof ds.id).toBe("string");
    expect(typeof ds.license).toBe("string");
    expect(typeof ds.source.accession).toBe("string");
    expect(ds.source.accession.length).toBeGreaterThan(0);
    expect(ds.files.length).toBeGreaterThanOrEqual(1);

    const f0 = ds.files[0];
    expect(fs.existsSync(f0.path)).toBe(true);
    const got = sha256File(f0.path);
    expect(got).toBe(f0.sha256);
  });
});
