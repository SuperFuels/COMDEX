#!/usr/bin/env python3
"""
Post-process G9 / G10 outputs and promote candidate discoveries.

Improvements:
- Robust, repo-relative paths (no cwd surprises)
- Searches BOTH repo root and backend/photon_algebra/tests for CSVs
- Tolerant header matching for G9/G10 signatures
- Defensive parsing; won't crash on odd rows/encodings
"""

import os, json, glob, csv, math, time, re
import numpy as np
from pathlib import Path

here = Path(__file__).resolve()
# utils -> photon_algebra -> backend -> <repo-root>
REPO = here.parents[3]  # was parents[2]
TEST_DIR  = REPO / "backend/photon_algebra" / "tests"
TEST_DIR.mkdir(parents=True, exist_ok=True)

LEDGER    = TEST_DIR / "discoveries.json"
CANDS     = TEST_DIR / "discovery_candidates.json"

# places to look for CSVs (newest-first scan)
SEARCH_DIRS = [
    REPO,                      # repo root (in case scripts dumped here)
    TEST_DIR,                  # canonical tests location
]

# ---------- utils ----------
def read_csv_generic(path: Path):
    try:
        with path.open(newline="") as f:
            r = csv.reader(f)
            rows = [row for row in r if row and not str(row[0]).strip().startswith("#")]
    except Exception:
        return {}, {}

    if not rows:
        return {}, {}

    # normalize header -> lower, strip spaces and special chars
    hdr_raw = [str(h).strip() for h in rows[0]]
    hdr_norm = [re.sub(r"[^a-zA-Z0-9_<>\.\-*κψ_]+", "", h.strip().lower()) for h in hdr_raw]

    data = {h: [] for h in hdr_raw}
    for row in rows[1:]:
        for h, v in zip(hdr_raw, row):
            v_str = str(v).strip()
            # try float (including scientific e/E); else NaN
            try:
                data[h].append(float(v_str))
            except Exception:
                try:
                    data[h].append(float(v_str.replace("e", "E")))
                except Exception:
                    data[h].append(np.nan)

    # views: original-case and normalized-lower
    lower = {hn: np.array(data[hr], dtype=float) for hr, hn in zip(hdr_raw, hdr_norm)}
    orig  = {hr: np.array(v, dtype=float) for hr, v in data.items()}
    return orig, lower

def list_csvs():
    files = []
    for d in SEARCH_DIRS:
        files += sorted(d.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    # de-dup while preserving order
    seen = set()
    out = []
    for p in files:
        if p.resolve() not in seen:
            seen.add(p.resolve())
            out.append(p)
    return out

def series_get(lower, *aliases):
    for a in aliases:
        if a in lower:
            return lower[a]
    return np.array([])

def safe_var(x):
    x = np.asarray(x); x = x[np.isfinite(x)]
    return float(np.var(x)) if x.size else float("nan")

def lagged_xcorr(x, y, max_lag=50):
    best = (0, 0.0)
    x = np.asarray(x); y = np.asarray(y)
    if len(x) < 16 or len(y) < 16:
        return best
    for lag in range(-max_lag, max_lag+1):
        if lag < 0:
            a, b = x[:lag], y[-lag:]
        elif lag > 0:
            a, b = x[lag:], y[:-lag]
        else:
            a, b = x, y
        a = a[np.isfinite(a)]; b = b[np.isfinite(b)]
        n = min(len(a), len(b))
        if n < 8:
            continue
        a, b = a[:n], b[:n]
        ca = (a - a.mean()); cb = (b - b.mean())
        denom = (np.linalg.norm(ca) * np.linalg.norm(cb) + 1e-12)
        corr = float(np.dot(ca, cb) / denom)
        if abs(corr) > abs(best[1]):
            best = (lag, corr)
    return best

def psd_slope_beta(x, fs=1.0):
    x = np.asarray(x); x = x[np.isfinite(x)]
    if x.size < 128: return float("nan")
    n = 256
    segs = max(1, len(x)//n)
    psd = np.zeros(n//2+1)
    win = np.hanning(n)
    for i in range(segs):
        seg = x[i*n:(i+1)*n]
        if len(seg) < n: break
        X = np.fft.rfft((seg - seg.mean()) * win)
        psd += (X*np.conj(X)).real
    psd /= max(segs,1)
    f = np.fft.rfftfreq(n, d=1.0/fs)
    mask = (f > (fs/n)*5) & (f < (fs/2)*0.5)
    f, p = f[mask], psd[mask]
    f, p = f[(p>0)], p[(p>0)]
    if len(f) < 10: return float("nan")
    beta, _ = np.polyfit(np.log10(f), np.log10(p), 1)
    return float(-beta)  # PSD ~ 1/f^beta

def linear_R2(x, y):
    x = np.asarray(x); y = np.asarray(y)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 10: return float("nan")
    A = np.vstack([x, np.ones_like(x)]).T
    m, c = np.linalg.lstsq(A, y, rcond=None)[0]
    yhat = m*x + c
    ss_res = np.sum((y - yhat)**2)
    ss_tot = np.sum((y - y.mean())**2) + 1e-12
    return float(1 - ss_res/ss_tot)

def contraction_score(series, step=50):
    s = np.asarray(series)
    s = s[np.isfinite(s)]
    if len(s) < 4*step: return float("nan")
    v1 = np.var(s[:step]); v2 = np.var(s[-step:])
    return float(v2 / (v1 + 1e-12))

# ---------- classification ----------
G9_ALIASES = {
    # energy
    "E": ("e","<e>","energy","total_e","e_mean","mean_e","⟨e⟩"),
    # psi*kappa coupling
    "PK": ("psi_kappa","psi.kappa","psi*κ","psikappa","<psi*κ>","coupling","psi_kappacorr"),
    # spectral entropy
    "SE": ("spectralentropy","spectral_entropy","entropy","s_entropy","entropy_spectrum")
}

G10_ALIASES = {
    "ST": ("stability","<stability>","stability_mean","regime_stability","stability_trace")
}

def looks_like_g9(cols: set, path_name: str) -> bool:
    has_pk = any(a in cols for a in G9_ALIASES["PK"])
    has_se = any(a in cols for a in G9_ALIASES["SE"])
    name_hint = bool(re.search(r"\bg9\b", path_name, re.I))
    return (has_pk and has_se) or name_hint

def looks_like_g10(cols: set, path_name: str) -> bool:
    has_st = any(a in cols for a in G10_ALIASES["ST"])
    name_hint = bool(re.search(r"\bg10\b", path_name, re.I))
    return has_st or name_hint

def find_series_files():
    g9, g10 = None, None
    for p in list_csvs():             # newest first
        data, lower = read_csv_generic(p)
        if not lower:
            continue
        cols = set(lower.keys())
        if g9 is None and looks_like_g9(cols, p.name):
            g9 = (p, data, lower)
        if g10 is None and looks_like_g10(cols, p.name):
            g10 = (p, data, lower)
        if g9 and g10:
            break
    return g9, g10

# ---------- main ----------
def main():
    cand = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
    g9, g10 = find_series_files()

    # --- G9 metrics ---
    if g9:
        g9p, g9d, g9l = g9
        E  = series_get(g9l, *G9_ALIASES["E"])
        PK = series_get(g9l, *G9_ALIASES["PK"])
        SE = series_get(g9l, *G9_ALIASES["SE"])

        lag, corr = lagged_xcorr(E, PK, max_lag=50)
        beta = psd_slope_beta(PK)
        R2   = linear_R2(np.diff(SE) if len(SE)>1 else SE,
                         np.diff(PK) if len(PK)>1 else PK)
        lam  = 1.0
        n = min(len(E), len(PK))
        I = (E[:n] + lam*PK[:n]) if n>0 else np.array([])
        I_cv = float(np.std(I)/ (np.mean(np.abs(I))+1e-12)) if len(I)>10 else float("nan")

        cand["G9"] = {
            "file": str(g9p.relative_to(REPO)),
            "lag_maxcorr": lag,
            "xcorr": corr,
            "psd_beta": beta,
            "entropy_coupling_R2": R2,
            "composite_invariant_cv": I_cv
        }
        print(f"* G9 source: {g9p}")

    # --- G10 metrics ---
    if g10:
        g10p, g10d, g10l = g10
        ST = series_get(g10l, *G10_ALIASES["ST"])
        step = max(20, len(ST)//10 if len(ST) else 20)
        ctr  = contraction_score(ST, step=step)
        cand["G10"] = {
            "file": str(g10p.relative_to(REPO)),
            "contraction_score": ctr
        }
        print(f"* G10 source: {g10p}")

    # save candidates
    with CANDS.open("w") as f:
        json.dump(cand, f, indent=2)
    print(f"✅ Candidates saved -> {CANDS.relative_to(REPO)}")

    # promote strong hits to ledger
    hits = []
    if "G9" in cand:
        g9m = cand["G9"]
        if (g9m.get("xcorr") or 0) > 0.3 and (g9m.get("lag_maxcorr") or 0) > 0:
            hits.append({"event":"Directional ψ->κ emergence","metrics":g9m})
        if 0.8 <= (g9m.get("psd_beta") or 0) <= 1.2:
            hits.append({"event":"Scale-free ψ*κ spectrum (β≈1)","metrics":g9m})
        if (g9m.get("entropy_coupling_R2") or 0) > 0.7:
            hits.append({"event":"Entropy-curvature reciprocity (high R2)","metrics":g9m})
        if (g9m.get("composite_invariant_cv") or 1) < 0.05:
            hits.append({"event":"Composite invariant conserved (I = E + λ⟨ψ*κ⟩)","metrics":g9m})

    if "G10" in cand:
        g10m = cand["G10"]
        if (g10m.get("contraction_score") or 2) < 1.0:
            hits.append({"event":"RG-style fixed point (variance contraction)","metrics":g10m})

    if hits:
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "series": "G9/G10",
            "discoveries": hits
        }
        try:
            if LEDGER.exists():
                with LEDGER.open() as f:
                    ledger = json.load(f)
            else:
                ledger = []
            if isinstance(ledger, dict):
                ledger = [ledger]
            ledger.append(entry)
            with LEDGER.open("w") as f:
                json.dump(ledger, f, indent=2)
            print(f"📘 Discovery ledger updated -> {LEDGER.relative_to(REPO)}")
        except Exception as e:
            print(f"⚠️ Could not append to ledger: {e}")
    else:
        print("i️ No strong discovery thresholds hit (data may be missing or headers unmatched).")

if __name__ == "__main__":
    main()