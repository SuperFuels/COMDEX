import { describe, it, expect } from "vitest";
import { runP18EvalV02 } from "../eval/p18/p18_eval_v02";

describe("P18.4 eval v0.2 determinism", () => {
  it("is deterministic except created_utc", () => {
    const a = runP18EvalV02();
    const b = runP18EvalV02();

    // normalize timestamps
    a.meta.created_utc = "X";
    b.meta.created_utc = "X";

    expect(a).toEqual(b);
  });
});
