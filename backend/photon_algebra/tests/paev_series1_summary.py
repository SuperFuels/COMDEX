#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Photon Algebra Evaluation (PAEV)
Series I — Summary Dashboard (Tests 1 → 7)
"""

import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
TABLE_DIR = "docs/theory/tables"
FIG_DIR = "docs/theory/figures"
os.makedirs(FIG_DIR, exist_ok=True)

print("⚙️  Generating PAEV Series I Summary...")

# ---------------------------------------------------------------------
# Load all available tables
# ---------------------------------------------------------------------
tables = sorted(glob.glob(os.path.join(TABLE_DIR, "PAEV_Test*.csv")))
if not tables:
    raise FileNotFoundError("No PAEV_Test*.csv tables found in docs/theory/tables")

data_summary = []
for path in tables:
    name = os.path.basename(path).replace(".csv", "")
    try:
        df = pd.read_csv(path)
        data_summary.append((name, df))
        print(f"✅ Loaded {name} ({len(df)} rows)")
    except Exception as e:
        print(f"⚠️ Could not parse {path}: {e}")

# ---------------------------------------------------------------------
# Unified Visibility Overview
# ---------------------------------------------------------------------
fig, axes = plt.subplots(3, 3, figsize=(12, 10))
axes = axes.ravel()

for ax, (name, df) in zip(axes, data_summary):
    cols = [c for c in df.columns if "V" in c]
    if not cols:
        continue
    for c in cols:
        ax.plot(df.index, df[c], marker="o", label=c)
    ax.set_title(name.replace("_", " "), fontsize=9)
    ax.set_xlabel("index")
    ax.set_ylabel("visibility V")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7)

for ax in axes[len(data_summary):]:
    ax.axis("off")

plt.suptitle("PAEV Series I — Unified Visibility Overview", fontsize=14)
plt.tight_layout(rect=[0, 0, 1, 0.97])
fig.savefig(os.path.join(FIG_DIR, "PAEV_SeriesI_Summary.png"), dpi=300)
print("✅ Saved figure → docs/theory/figures/PAEV_SeriesI_Summary.png")

# ---------------------------------------------------------------------
# Numerical Synthesis Table
# ---------------------------------------------------------------------
summary_rows = []
for name, df in data_summary:
    numeric_cols = [c for c in df.columns if "V" in c]
    if not numeric_cols:
        continue
    means = df[numeric_cols].mean().to_dict()
    stds = df[numeric_cols].std().to_dict()
    row = {"test": name}
    for k in means:
        row[f"{k}_mean"] = means[k]
        row[f"{k}_std"] = stds[k]
    summary_rows.append(row)

summary_df = pd.DataFrame(summary_rows)
summary_path = os.path.join(TABLE_DIR, "PAEV_SeriesI_Summary.csv")
summary_df.to_csv(summary_path, index=False, float_format="%.5f")
print(f"✅ Saved summary table → {summary_path}")

print("🏁 PAEV Series I Summary complete.")