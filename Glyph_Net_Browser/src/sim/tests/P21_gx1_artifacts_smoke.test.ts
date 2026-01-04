import { describe, it, expect } from "vitest";
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { P21_GX1 } from "../contracts/p21_gx1_contract";

function sh(cmd: string, args: string[], cwd: string) {
  return execFileSync(cmd, args, { cwd, stdio: "pipe", encoding: "utf-8" });
}

describe("P21_GX1 artifacts smoke", () => {
  it("artifact ladder exists and checksums verify", () => {
    const repoRoot = "/workspaces/COMDEX";
    const root = join(repoRoot, P21_GX1.artifactRoot);

    expect(existsSync(root)).toBe(true);

    const latestPath = join(root, "runs", "LATEST_RUN_ID.txt");
    expect(existsSync(latestPath)).toBe(true);

    const runId = readFileSync(latestPath, "utf-8").trim();
    expect(runId.length).toBeGreaterThan(0);

    // sha256sum -c checksums/<RUN_ID>.sha256
    const out1 = sh("bash", ["-lc", `cd "${root}" && sha256sum -c "checksums/${runId}.sha256"`], repoRoot);
    expect(out1).toContain(": OK");

    // sha256sum -c ARTIFACTS_INDEX.sha256
    const out2 = sh("bash", ["-lc", `cd "${root}" && sha256sum -c "ARTIFACTS_INDEX.sha256"`], repoRoot);
    expect(out2).toContain("ARTIFACTS_INDEX.md: OK");
  });
});
