import { loadP16MetricsContract } from "../../calibration/p16/metrics/p16_metrics_contract";
import { loadP16DatasetRegistry } from "../../calibration/p16/datasets/p16_datasets";
import { loadP17OutputContract } from "../../compiler/p17/p17_recommender_output_contract";
import fs from "node:fs";

export type P18EvalContract = {
  schemaVersion: "P18_EVAL_CONTRACT_V0";
  status: "ROADMAP_UNTIL_P16_CALIBRATED_AND_DATA_FROZEN" | "PILOT_FROZEN_V1_EVAL_READY";
  inputs: {
    p17OutputContractPath: string;
    p16MetricsContractPath: string;
    p16DatasetsRegistryPath: string;
  };
  output: { reportSchemaVersion: "P18_EVAL_REPORT_V0" };
  guardrails: {
    noWetlabClaims: boolean;
    noEditSuccessClaims: boolean;
    contractOnly: boolean;
  };
};

export function getP18EvalContract(): P18EvalContract {
  return {
    schemaVersion: "P18_EVAL_CONTRACT_V0",
    status: "PILOT_FROZEN_V1_EVAL_READY",
    inputs: {
      p17OutputContractPath:
        "Glyph_Net_Browser/src/sim/compiler/p17/p17_recommender_output_contract.json",
      p16MetricsContractPath:
        "Glyph_Net_Browser/src/sim/calibration/p16/metrics/p16_metrics_contract.json",
      p16DatasetsRegistryPath:
        "Glyph_Net_Browser/src/sim/calibration/p16/datasets/p16_datasets.json",
    },
    output: { reportSchemaVersion: "P18_EVAL_REPORT_V0" },
    guardrails: {
      noWetlabClaims: true,
      noEditSuccessClaims: true,
      contractOnly: true,
    },
  };
}

export type P18MetricResult = {
  metricId: string;
  estimate: number;
  ciLower: number;
  ciUpper: number;
  nullEstimate: number;
  pValue: number; // two-sided permutation p-value
  pass: boolean;
  notes?: string[];
};

export type P18EvalReport = {
  schemaVersion: "P18_EVAL_REPORT_V0";
  status: "ROADMAP_STUB" | "PILOT_FROZEN_V1_REALMETRIC";
  evaluatedAtUTC: string;
  inputs: {
    p17OutputContractPath: string;
    p16MetricsContractPath: string;
    p16DatasetsRegistryPath: string;
  };
  summary: {
    outputsSeen: number;
    candidatesSeen: number;
    metricIdsReferenced: string[];
    datasetIdsUsed: string[];
  };
  results: P18MetricResult[];
  notes: string[];
};

/** Deterministic LCG RNG (stable across JS engines). */
function makeLCG(seed: number) {
  let s = seed >>> 0;
  return {
    nextU32() {
      s = (Math.imul(1664525, s) + 1013904223) >>> 0;
      return s;
    },
    nextFloat01() {
      return this.nextU32() / 0x100000000;
    },
    nextInt(n: number) {
      return Math.floor(this.nextFloat01() * n);
    },
  };
}

type SeqRow = { id: string; label: "pos" | "neg"; seq: string };

function loadPilotTSV(path: string): SeqRow[] {
  const txt = fs.readFileSync(path, "utf8").trim();
  const lines = txt.split(/\r?\n/);
  const out: SeqRow[] = [];
  for (let i = 1; i < lines.length; i++) {
    const [id, label, sequence] = lines[i].split("\t");
    if (!id || !label || !sequence) continue;
    if (label !== "pos" && label !== "neg") continue;
    out.push({ id, label, seq: sequence });
  }
  return out;
}

function hasMotif(seq: string, motif: string): boolean {
  return seq.includes(motif);
}

/**
 * Metric: log2 odds ratio of motif presence between pos and neg.
 * odds = p/(1-p). Use Jeffreys-style pseudocount 0.5 on counts.
 */
function motifLog2Odds(rows: SeqRow[], motif: string, labels?: ("pos" | "neg")[]): number {
  const use = labels
    ? rows.map((r, i) => ({ ...r, label: labels[i] }))
    : rows;

  let posHit = 0, posTot = 0, negHit = 0, negTot = 0;
  for (const r of use) {
    const hit = hasMotif(r.seq, motif) ? 1 : 0;
    if (r.label === "pos") { posTot++; posHit += hit; }
    else { negTot++; negHit += hit; }
  }

  // pseudocount on hits/misses
  const posMiss = posTot - posHit;
  const negMiss = negTot - negHit;

  const a = posHit + 0.5;
  const b = posMiss + 0.5;
  const c = negHit + 0.5;
  const d = negMiss + 0.5;

  const oddsPos = a / b;
  const oddsNeg = c / d;
  const or = oddsPos / oddsNeg;

  return Math.log2(or);
}

function bootstrapCI(rows: SeqRow[], motif: string, n: number, seed: number): { lo: number; hi: number } {
  const rng = makeLCG(seed);
  const pos = rows.filter((r) => r.label === "pos");
  const neg = rows.filter((r) => r.label === "neg");

  const stats: number[] = [];
  for (let i = 0; i < n; i++) {
    const sample: SeqRow[] = [];
    for (let j = 0; j < pos.length; j++) sample.push(pos[rng.nextInt(pos.length)]);
    for (let j = 0; j < neg.length; j++) sample.push(neg[rng.nextInt(neg.length)]);
    stats.push(motifLog2Odds(sample, motif));
  }
  stats.sort((a, b) => a - b);
  const lo = stats[Math.floor(0.025 * (stats.length - 1))];
  const hi = stats[Math.floor(0.975 * (stats.length - 1))];
  return { lo, hi };
}

function permutationPValue(rows: SeqRow[], motif: string, n: number, seed: number, observed: number): { p: number; nullMean: number } {
  const rng = makeLCG(seed);
  const labels = rows.map((r) => r.label);
  const stats: number[] = [];

  function shuffleInPlace<T>(arr: T[]) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = rng.nextInt(i + 1);
      const tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
    }
  }

  for (let i = 0; i < n; i++) {
    const perm = labels.slice();
    shuffleInPlace(perm);
    stats.push(motifLog2Odds(rows, motif, perm));
  }

  const nullMean = stats.reduce((s, x) => s + x, 0) / stats.length;

  // two-sided: compare absolute deviation from 0 (or from nullMean). We use |stat| >= |obs|
  const obsAbs = Math.abs(observed);
  let extreme = 0;
  for (const x of stats) if (Math.abs(x) >= obsAbs) extreme++;
  const p = (extreme + 1) / (stats.length + 1); // add-one smoothing

  return { p, nullMean };
}

/**
 * P18 v0.1: compute real metric(s) against frozen pilot dataset.
 * Still contract-only: no wetlab claims, no edit success claims.
 */
export function evalP18v01(): P18EvalReport {
  const c = getP18EvalContract();
  const out = loadP17OutputContract(c.inputs.p17OutputContractPath);
  const m = loadP16MetricsContract(c.inputs.p16MetricsContractPath);
  const dreg = loadP16DatasetRegistry(c.inputs.p16DatasetsRegistryPath);

  const metricIds = new Set<string>();
  let candidates = 0;

  for (const o of out.outputs) {
    for (const cand of o.candidates) {
      candidates++;
      for (const p of cand.predictions) metricIds.add(p.metricId);
    }
  }

  // enforce metric universe
  const known = new Set(m.metrics.map((x) => x.id));
  for (const id of metricIds) {
    if (!known.has(id)) throw new Error(`P18 eval v0.1: unknown metricId referenced: ${id}`);
  }

  // pilot: expect exactly one dataset + one metric
  if (dreg.datasets.length < 1) throw new Error("P18 eval v0.1: no datasets in registry");
  const ds = dreg.datasets[0];
  if (!ds.files || ds.files.length < 1) throw new Error("P18 eval v0.1: dataset has no files[]");
  const file0 = ds.files[0].path;

  const rows = loadPilotTSV(file0);
  if (rows.length < 4) throw new Error("P18 eval v0.1: pilot dataset too small to evaluate");

  const results: P18MetricResult[] = [];
  const seed = 1337;

  for (const id of Array.from(metricIds).sort()) {
    if (id !== "P16_MOTIF_LOG2_ODDS_TATA") {
      throw new Error(`P18 eval v0.1: only P16_MOTIF_LOG2_ODDS_TATA supported in pilot, got ${id}`);
    }

    const estimate = motifLog2Odds(rows, "TATA");
    const ci = bootstrapCI(rows, "TATA", 1000, seed);
    const perm = permutationPValue(rows, "TATA", 1000, seed, estimate);

    const pass = estimate >= 1.0 && perm.p <= 0.05;

    results.push({
      metricId: id,
      estimate,
      ciLower: ci.lo,
      ciUpper: ci.hi,
      nullEstimate: perm.nullMean,
      pValue: perm.p,
      pass,
      notes: [
        "Pilot metric: literal motif presence enrichment (sanity only).",
        "Deterministic bootstrap/permutation with fixed seed.",
      ],
    });
  }

  return {
    schemaVersion: "P18_EVAL_REPORT_V0",
    status: "PILOT_FROZEN_V1_REALMETRIC",
    evaluatedAtUTC: new Date().toISOString(),
    inputs: c.inputs,
    summary: {
      outputsSeen: out.outputs.length,
      candidatesSeen: candidates,
      metricIdsReferenced: Array.from(metricIds).sort(),
      datasetIdsUsed: [ds.id],
    },
    results,
    notes: [
      "PILOT: real metric computed on frozen in-repo dataset.",
      "No datasets downloaded at runtime; no preprocessing pipeline beyond deterministic parsing; no biological claims.",
    ],
  };
}

/** Back-compat stub (kept): contract-only shape check. */
export function evalP18Stub(): P18EvalReport {
  // preserve older behavior by delegating to v0.1 now that we have a real pilot
  return evalP18v01();
}
