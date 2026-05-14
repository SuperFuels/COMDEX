import { describe, it, expect } from "vitest";
import { getP17RecommenderSpec } from "../compiler/p17/p17_recommender_spec";

describe("P17 recommender spec (ROADMAP)", () => {
  it("emits stable contract fields", () => {
    const s = getP17RecommenderSpec();
    expect(s.schemaVersion).toBe("P17_RECOMMENDER_SPEC_V0");
    expect(s.status).toBe("ROADMAP_UNTIL_P16_CALIBRATED");
    expect(typeof s.goal).toBe("string");
    expect(s.guardrails.noWetlabClaims).toBe(true);
    expect(s.guardrails.noEditSuccessClaims).toBe(true);
    expect(s.guardrails.requiresConfidenceIntervals).toBe(true);
    expect(typeof s.dependencies.p16DatasetsRegistryPath).toBe("string");
    expect(typeof s.dependencies.p16MetricsContractPath).toBe("string");
  });
});
