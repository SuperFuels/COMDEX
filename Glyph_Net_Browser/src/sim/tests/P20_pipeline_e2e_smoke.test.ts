import { describe, it, expect } from "vitest";
import { getP20PipelineSpec } from "../pipeline/p20/p20_pipeline_spec";
import { runP19Stub } from "../pipeline/p19/p19_run_contract";
import { loadP16MetricsContract } from "../calibration/p16/metrics/p16_metrics_contract";

describe("P20 pipeline E2E smoke (ROADMAP)", () => {
  it("runs P19 -> P18 and metric ids remain inside P16 metric universe", () => {
    const spec = getP20PipelineSpec();
    expect(spec.schemaVersion).toBe("P20_PIPELINE_SPEC_V0");
    expect(spec.guardrails.contractOnly).toBe(true);
    expect(spec.guardrails.noWetlabClaims).toBe(true);
    expect(spec.guardrails.noEditSuccessClaims).toBe(true);

    const r = runP19Stub();
    expect(r.schemaVersion).toBe("P19_RUN_REPORT_V0");
    expect(r.status).toBe("ROADMAP_STUB");
    expect(r.summary.outputsSeen).toBeGreaterThanOrEqual(1);
    expect(r.summary.candidatesSeen).toBeGreaterThanOrEqual(1);

    const m = loadP16MetricsContract(spec.wiring.p16MetricsContractPath);
    const known = new Set(m.metrics.map((x) => x.id));
    for (const id of r.summary.metricIdsReferenced) {
      expect(known.has(id)).toBe(true);
    }
  });
});
