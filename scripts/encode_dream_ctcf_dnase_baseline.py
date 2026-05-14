import os, json
import numpy as np
import pandas as pd
import pyranges as pr
from sklearn.metrics import roc_auc_score, average_precision_score

LABELS = os.getenv("LABELS", "/workspaces/COMDEX/tmp/encode_dream/labels/CTCF.train.labels.tsv")
PEAKS  = os.getenv("PEAKS",  "/workspaces/COMDEX/tmp/encode_dream/dnase/DNASE.PC-3.conservative.narrowPeak")
CELL   = os.getenv("CELL",   "PC-3")
OUT_JSON = os.getenv("OUT_JSON", "/workspaces/COMDEX/backend/modules/knowledge/encode_dream_ctcf_dnase_baseline.json")

CHUNK_SIZE  = int(os.getenv("CHUNK_SIZE", "500000"))
MAX_WINDOWS = os.getenv("MAX_WINDOWS", "").strip()
MAX_WINDOWS = int(MAX_WINDOWS) if MAX_WINDOWS else None

# ---- load DNase peaks ----
peaks = pd.read_csv(PEAKS, sep="\t", header=None, compression="infer")
if peaks.shape[1] < 7:
    raise SystemExit(f"Peak file looks wrong: expected >=7 cols, got {peaks.shape[1]}")

peaks = peaks.iloc[:, :9].copy()
cols = ["Chromosome","Start","End","name","score","strand","signal","p","q"][:peaks.shape[1]]
peaks.columns = cols
peaks["Chromosome"] = peaks["Chromosome"].astype(str)
peaks["Start"] = peaks["Start"].astype(np.int64)
peaks["End"]   = peaks["End"].astype(np.int64)
peaks["signal"] = pd.to_numeric(peaks["signal"], errors="coerce").fillna(0.0).astype(np.float32)

gr_p = pr.PyRanges(peaks[["Chromosome","Start","End","signal"]])

# ---- stream labels -> spill y + scores to disk ----
tmp_dir = "/workspaces/COMDEX/tmp/encode_dream/_tmp_metrics"
os.makedirs(tmp_dir, exist_ok=True)
y_path = os.path.join(tmp_dir, "y.uint8.bin")
s_path = os.path.join(tmp_dir, "scores.float32.bin")

# truncate any previous run
open(y_path, "wb").close()
open(s_path, "wb").close()

n_total = 0

usecols = ["chr","start","stop", CELL]
dtypes  = {"chr":"string", "start":"int32", "stop":"int32", CELL:"string"}

for chunk in pd.read_csv(LABELS, sep="\t", usecols=usecols, dtype=dtypes, chunksize=CHUNK_SIZE):
    y_raw = chunk[CELL].astype(str)
    keep = y_raw.isin(["B","U"])  # drop A
    if not keep.any():
        continue

    w = chunk.loc[keep, ["chr","start","stop"]].copy()
    w.columns = ["Chromosome","Start","End"]
    w["Chromosome"] = w["Chromosome"].astype(str)
    w["Start"] = w["Start"].astype(np.int64)
    w["End"]   = w["End"].astype(np.int64)

    y = (y_raw.loc[keep] == "B").astype(np.uint8).to_numpy()
    m = len(y)

    # numeric id per window (avoid string keys)
    w["w_id"] = np.arange(m, dtype=np.int64)

    gr_w = pr.PyRanges(w)
    joined = gr_w.join(gr_p)

    scores = np.zeros(m, dtype=np.float32)
    jdf = joined.df
    if len(jdf) > 0:
        maxsig = jdf.groupby("w_id")["signal"].max()
        scores[maxsig.index.to_numpy(dtype=np.int64)] = maxsig.to_numpy(dtype=np.float32)

    y.tofile(y_path)
    scores.tofile(s_path)

    n_total += m
    if MAX_WINDOWS is not None and n_total >= MAX_WINDOWS:
        break

# ---- compute exact metrics from written bins ----
y_mm = np.memmap(y_path, dtype=np.uint8, mode="r")
s_mm = np.memmap(s_path, dtype=np.float32, mode="r")

if len(y_mm) != len(s_mm):
    raise SystemExit(f"Length mismatch: y={len(y_mm)} scores={len(s_mm)}")

positives = int(np.asarray(y_mm).sum())
negatives = int(len(y_mm) - positives)

if len(np.unique(y_mm)) < 2:
    auroc = float("nan")
    auprc = float("nan")
else:
    auroc = float(roc_auc_score(y_mm, s_mm))
    auprc = float(average_precision_score(y_mm, s_mm))

out = {
  "dataset": "ENCODE-DREAM TF binding (within-cell-type)",
  "tf": "CTCF",
  "cell": CELL,
  "features": "DNase narrowPeak signal (max overlap, else 0)",
  "labels": "B=1, U=0; A dropped",
  "labels_file": LABELS,
  "peaks_file": PEAKS,
  "n_windows": int(len(y_mm)),
  "positives": positives,
  "negatives": negatives,
  "metric": {"AUROC": auroc, "AUPRC": auprc},
  "tmp_artifacts": {"y_bin": y_path, "scores_bin": s_path},
}

os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
with open(OUT_JSON, "w") as f:
    json.dump(out, f, indent=2)

print("Wrote:", OUT_JSON)
print(json.dumps(out, indent=2))
