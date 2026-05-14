import { describe, it, expect } from "vitest";
import { loadP15PreprocessContract } from "../portability/preprocess/p15_preprocess_contract";

describe("P15.2 preprocess contract (ROADMAP)", () => {
  it("parses and exposes required fields", () => {
    const c = loadP15PreprocessContract(
      "Glyph_Net_Browser/src/sim/portability/preprocess/p15_preprocess_contract.json"
    );

    expect(c.schemaVersion).toBe("P15_PREPROCESS_CONTRACT_V0");
    expect(c.status).toBe("ROADMAP_UNTIL_FROZEN");
    expect(c.id).toBe("P15_PREPROCESS_V0_TBD");

    expect(typeof c.pipelineVersion).toBe("string");
    expect(typeof c.pipelineHash).toBe("string");
    expect(Array.isArray(c.determinism)).toBe(true);

    expect(Array.isArray(c.inputs)).toBe(true);
    expect(Array.isArray(c.outputs)).toBe(true);
  });
});
