#!/usr/bin/env python3
"""
Phase 34 - Latent Concept Topology Map
- Builds per-concept feature vectors from evolution + resonance logs
- Reduces to 2D (PCA fallback; uses only stdlib deps + numpy/pandas/matplotlib)
- Saves scatter + CSV for downstream analytics

Outputs:
  data/analysis/concept_latent_map.png
  data/analysis/concept_latent_map.csv
"""
import os, json, math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

EVOL_LOG = Path("data/analysis/concept_evolution_log.jsonl")
STREAM   = Path("data/feedback/resonance_stream.jsonl")
OUT_IMG  = Path("data/analysis/concept_latent_map.png")
OUT_CSV  = Path("data/analysis/concept_latent_map.csv")

def _safe_jsonl(path: Path):
    if not path.exists(): return []
    rows = []
    with path.open() as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try: rows.append(json.loads(line))
            except: pass
    return rows

def pca_2d(X: np.ndarray):
    # Center
    Xc = X - X.mean(0, keepdims=True)
    # Cov + eig
    C = np.cov(Xc, rowvar=False)
    vals, vecs = np.linalg.eigh(C)
    order = np.argsort(vals)[::-1][:2]
    W = vecs[:, order]
    Y = Xc @ W
    return Y

def main():
    EVOL_LOG.parent.mkdir(parents=True, exist_ok=True)
    OUT_IMG.parent.mkdir(parents=True, exist_ok=True)

    evol = _safe_jsonl(EVOL_LOG)
    stream = _safe_jsonl(STREAM)

    # --- Per-concept event tallies
    tallies = {}
    def bump(c, k):
        d = tallies.setdefault(c, {"fusion":0,"speciation":0,"reinforce":0,"decay":0,"cooldown":0})
        d[k] = d.get(k,0) + 1

    for e in evol:
        et = e.get("type")
        if et == "fusion":
            # standardize: "fusion" events you logged via evolve_concepts()
            result = e.get("result") or {}
            newc  = result if isinstance(result,str) else result.get("new") or ""
            parents = e.get("sources") or e.get("concepts") or []
            for p in parents: bump(p, "fusion")
            if newc: bump(newc, "fusion")
        elif et == "speciation":
            parent = (e.get("sources") or [""])[0]
            subs   = e.get("result") or e.get("concept") or []
            bump(parent,"speciation")
            if isinstance(subs,list):
                for s in subs: bump(s,"speciation")
        elif et == "reinforce":
            for c in e.get("concepts", []):
                bump(c,"reinforce")
        elif et == "decay":
            for c in e.get("concepts", []):
                bump(c,"decay")
        elif et == "cooldown":
            for c in e.get("concepts", []):
                bump(c,"cooldown")

    # --- Stream RSI per symbol -> concept aggregation
    try:
        from backend.modules.aion_knowledge import knowledge_graph_core as akg
        cmap = akg.export_concepts()  # concept -> [symbols]
        sym_to_con = {}
        for c, syms in cmap.items():
            for s in syms: sym_to_con.setdefault(s, set()).add(c)
    except Exception:
        cmap, sym_to_con = {}, {}

    rsi_by_concept = {}
    for evt in stream:
        sym = evt.get("symbol") or evt.get("actual") or evt.get("predicted") or None
        rsi = evt.get("RSI")
        if sym is None or rsi is None: continue
        for c in sym_to_con.get(str(sym), []):
            rsi_by_concept.setdefault(c, []).append(float(rsi))

    rows = []
    allc = set(tallies.keys()) | set(rsi_by_concept.keys())
    if cmap: allc |= set(cmap.keys())
    for c in sorted(allc):
        t = tallies.get(c, {})
        rsis = rsi_by_concept.get(c, [])
        mean_rsi = float(np.mean(rsis)) if rsis else np.nan
        var_rsi  = float(np.var(rsis))  if rsis else np.nan
        deg = sum(int(v>0) for v in t.values())
        rows.append({
            "concept": c,
            "fusions": t.get("fusion",0),
            "speciations": t.get("speciation",0),
            "reinforcements": t.get("reinforce",0),
            "decays": t.get("decay",0),
            "cooldowns": t.get("cooldown",0),
            "mean_rsi": mean_rsi,
            "var_rsi": var_rsi,
            "degree": deg,
        })

    if not rows:
        print("⚠️ No concept data to embed.")
        return

    df = pd.DataFrame(rows).fillna(0.0)

    # Feature matrix: event counts + RSI stats + degree
    feats = df[["fusions","speciations","reinforcements","decays","cooldowns","mean_rsi","var_rsi","degree"]].to_numpy(dtype=float)
    # Guard constant columns
    if feats.shape[0] < 3:
        Y = np.hstack([feats[:, :1], feats[:, :1]])
    else:
        Y = pca_2d(feats)

    df["x"], df["y"] = Y[:,0], Y[:,1]
    df.to_csv(OUT_CSV, index=False)

    plt.figure(figsize=(9,7))
    s = 20 + 40*np.tanh(1+df["degree"].to_numpy())
    plt.scatter(df["x"], df["y"], s=s)
    for i, row in df.iterrows():
        if row["degree"]>=2 or row["fusions"]>0:
            plt.text(row["x"], row["y"], row["concept"][:28], fontsize=7)
    plt.title("Concept Latent Map (PCA)")
    plt.xlabel("PC1"); plt.ylabel("PC2")
    plt.tight_layout()
    plt.savefig(OUT_IMG, dpi=140)
    print(f"✅ Latent map saved -> {OUT_IMG}")
    print(f"🧾 CSV saved -> {OUT_CSV}")

if __name__ == "__main__":
    main()