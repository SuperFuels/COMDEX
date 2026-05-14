export type P15Prediction = {
  id: string;
  dataset: { name: string; version: string };
  preprocessing: { version: string; hash?: string };
  metrics: Array<{ name: string; expected: string; tolerance?: string }>;
  controls: { negatives: string[]; ablations: string[] };
  passFailRule: string;
};

export type P15Spec = {
  status: "ROADMAP_UNTIL_EXTERNAL_ANCHORS";
  mappings: {
    message: string;
    key: string;
    topology: string;
    separation: string;
  };
  predictions: P15Prediction[];
};

export function getP15SpecSkeleton(): P15Spec {
  return {
    status: "ROADMAP_UNTIL_EXTERNAL_ANCHORS",
    mappings: {
      message: "message ↔ measurable assay signal (TBD; assay class + units + acquisition)",
      key: "key ↔ motif/binding family (TBD; motif DB + matching rule)",
      topology: "topology ↔ contact/adjacency/cofactor graph proxy (TBD; assay + resolution)",
      separation: "separation ↔ orthogonality metric in binding/contact space (TBD; metric + null model)",
    },
    predictions: [
      {
        id: "P15-PRED-0001",
        dataset: {
          name: "ENCODE (candidate) — TF ChIP-seq + matched controls",
          version: "TBD_ACCESSION_SET_AND_FREEZE",
        },
        preprocessing: {
          version: "P15_PREPROCESS_V0_TBD",
          hash: "TBD_PIPELINE_HASH",
        },
        metrics: [
          {
            name: "motif_enrichment_delta",
            expected: "targeted motif family enrichment vs matched negatives (directional; TBD)",
            tolerance: "TBD",
          },
          {
            name: "selectivity_vs_background",
            expected: "signal separation between keyed vs unkeyed sites under null (TBD)",
            tolerance: "TBD",
          },
        ],
        controls: {
          negatives: ["shuffle_keys_preserve_gc", "scramble_motif_positions", "random_matched_regions"],
          ablations: ["remove_key_constraint", "remove_topology_proxy", "remove_separation_term"],
        },
        passFailRule:
          "TBD: pre-register null model + p-value/FDR + effect size threshold; must pass negatives and fail ablations appropriately.",
      },
    ],
  };
}
