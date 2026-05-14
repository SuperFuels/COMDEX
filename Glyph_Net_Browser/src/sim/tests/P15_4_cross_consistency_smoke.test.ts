import { describe, it, expect } from "vitest";
import { loadP15DatasetRegistry } from "../portability/datasets/p15_datasets";
import { loadP15PreprocessContract } from "../portability/preprocess/p15_preprocess_contract";
import { loadP15PredictionRegistry } from "../portability/predictions/p15_predictions";

describe("P15.4 portability bridge cross-consistency (ROADMAP)", () => {
  it("prediction.datasetId exists and prediction.preprocessContractId matches contract id", () => {
    const datasets = loadP15DatasetRegistry(
      "Glyph_Net_Browser/src/sim/portability/datasets/p15_datasets.json"
    );
    const contract = loadP15PreprocessContract(
      "Glyph_Net_Browser/src/sim/portability/preprocess/p15_preprocess_contract.json"
    );
    const preds = loadP15PredictionRegistry(
      "Glyph_Net_Browser/src/sim/portability/predictions/p15_predictions.json"
    );

    const datasetIds = new Set(datasets.datasets.map((d) => d.id));

    for (const p of preds.predictions) {
      expect(datasetIds.has(p.datasetId)).toBe(true);
      expect(p.preprocessContractId).toBe(contract.id);
    }
  });
});
