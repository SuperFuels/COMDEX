import { describe, it, expect } from "vitest";
import { getP18EvalContract } from "../eval/p18/p18_eval_contract";

describe("P18 eval contract (ROADMAP)", () => {
  it("exposes stable wiring fields", () => {
    const c = getP18EvalContract();
    expect(c.schemaVersion).toBe("P18_EVAL_CONTRACT_V0");
    expect(c.status).toBe("ROADMAP_UNTIL_P16_CALIBRATED_AND_DATA_FROZEN");
    expect(typeof c.inputs.p17OutputContractPath).toBe("string");
    expect(typeof c.inputs.p16MetricsContractPath).toBe("string");
    expect(c.output.reportSchemaVersion).toBe("P18_EVAL_REPORT_V0");
    expect(c.guardrails.noWetlabClaims).toBe(true);
    expect(c.guardrails.noEditSuccessClaims).toBe(true);
    expect(c.guardrails.contractOnly).toBe(true);
  });
});
