import { describe, it, expect } from "vitest";
import { getP19RunContract } from "../pipeline/p19/p19_run_contract";

describe("P19 run contract (ROADMAP)", () => {
  it("exposes stable wiring + guardrails", () => {
    const c = getP19RunContract();
    expect(c.schemaVersion).toBe("P19_RUN_CONTRACT_V0");
    expect(c.status).toBe("ROADMAP_UNTIL_P16_CALIBRATED_AND_DATA_FROZEN");
    expect(c.inputs.p18EvalContractPath).toBe(
      "Glyph_Net_Browser/src/sim/eval/p18/p18_eval_contract.ts"
    );
    expect(c.output.reportSchemaVersion).toBe("P19_RUN_REPORT_V0");
    expect(c.guardrails.contractOnly).toBe(true);
    expect(c.guardrails.noWetlabClaims).toBe(true);
    expect(c.guardrails.noEditSuccessClaims).toBe(true);
  });
});
