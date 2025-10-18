import json
import math
from pathlib import Path
from datetime import datetime, UTC
from string import Template

LATEST_FILE  = Path("data/ledger/awareness_latest.json")
SUMMARY_FILE = Path("data/ledger/awareness_sessions_summary.jsonl")
EXPORT_FILE  = Path("docs/latex/appendix_c_awareness_sessions.tex")
IMG_DIR      = Path("data/visualizations/awareness_sessions")
MAX_ENTRIES  = 10  # most recent N to show in table
APPEND_MODE  = True  # ✅ Phase 6.4 — append new session blocks

# ────────────────────────────────────────────────
#  TeX template
# ────────────────────────────────────────────────
TEX_TEMPLATE = Template(r"""
\section*{Appendix C — GHX Awareness Session Timeline}
\addcontentsline{toc}{section}{Appendix C — GHX Awareness Session Timeline}

\subsection*{Run ID: $run_id}
\textbf{Date:} $timestamp\\
\textbf{Closure State:} $closure_state\\
\textbf{Gain:} $gain \quad
\textbf{Stability (S):} $S \quad
\textbf{Resonance (R):} $R \\
\textbf{Coherence (Φ):} $Phi\\

\begin{figure}[H]
\centering
\includegraphics[width=0.95\linewidth]{$img_path}
\caption{Awareness trace $$\Phi(t)$$, $$R(t)$$ for $run_id.}
\end{figure}
""")

# ────────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────────
def _is_nan(x): return isinstance(x, float) and math.isnan(x)

def fmt_num(x, fmt, default="--"):
    try:
        if x is None or _is_nan(x): return default
        return format(float(x), fmt)
    except Exception:
        return default

def fmt_ts(ts):
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(float(ts), tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
        if hasattr(ts, "timestamp"):
            return datetime.fromtimestamp(ts.timestamp(), tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return str(ts)

def load_summary_records():
    """Read JSONL, deduplicate by timestamp, sort ascending."""
    if not SUMMARY_FILE.exists():
        return []
    entries, seen = [], set()
    for ln in SUMMARY_FILE.read_text().splitlines():
        if not ln.strip():
            continue
        try:
            j = json.loads(ln)
            ts = j.get("timestamp")
            if ts in seen: continue
            seen.add(ts)
            entries.append(j)
        except Exception:
            continue
    entries.sort(key=lambda j: j.get("timestamp") or 0)
    return entries[-MAX_ENTRIES:]

def find_latest_image():
    imgs = sorted(IMG_DIR.glob("awareness_*.png"), key=lambda p: p.stat().st_mtime)
    return str(imgs[-1]) if imgs else "data/visualizations/awareness_sessions/awareness_latest.png"

# ────────────────────────────────────────────────
#  Exporter (Append mode)
# ────────────────────────────────────────────────
def export_latest():
    summary = load_summary_records()
    if not summary:
        print("⚠️ No awareness sessions found in summary file.")
        return

    latest = summary[-1]
    phi  = latest.get("Phi") or latest.get("Φ") or latest.get("Φ_mean")
    R    = latest.get("R") or latest.get("resonance_index")
    Sval = latest.get("S") or latest.get("stability")
    gain = latest.get("gain")
    state = latest.get("closure_state") or latest.get("state", "--")
    ts = latest.get("timestamp")

    phi_s  = fmt_num(phi,  ".6f")
    R_s    = fmt_num(R,    ".12f")
    gain_s = fmt_num(gain, ".2f")
    S_s    = fmt_num(Sval, ".3f") if isinstance(Sval, (int, float)) else str(Sval or "--")
    ts_s   = fmt_ts(ts)

    run_id = f"RQC–Φ{len(summary):03d}"
    img_path = find_latest_image()

    tex_sub = rf"""
\subsection*{{Run ID: {run_id}}}
\textbf{{Date:}} {ts_s}\\
\textbf{{Closure State:}} {state}\\
\textbf{{Gain:}} {gain_s} \quad
\textbf{{Stability (S):}} {S_s} \quad
\textbf{{Resonance (R):}} {R_s} \\
\textbf{{Coherence (Φ):}} {phi_s}\\

\begin{{figure}}[H]
\centering
\includegraphics[width=0.95\linewidth]{{{img_path}}}
\caption{{Awareness trace $\Phi(t)$, $R(t)$ for {run_id}.}}
\end{{figure}}
"""

    table_rows = []
    for i, j in enumerate(summary, start=1):
        rid = f"RQC–Φ{i:03d}"
        date = fmt_ts(j.get("timestamp"))
        phi  = fmt_num(j.get("Phi") or j.get("Φ_mean"), ".6f")
        Rv   = fmt_num(j.get("R") or j.get("resonance_index"), ".6f")
        state = j.get("closure_state", "--")
        table_rows.append(f"{rid} & {date} & {phi} & {Rv} & {state} \\\\")

    table_block = r"""
\subsection*{Session Summary}
\begin{table}[H]
\centering
\begin{tabular}{lllll}
\toprule
Run ID & Date (UTC) & Φ (coh.) & R (res.) & State \\
\midrule
""" + "\n".join(table_rows) + r"""
\bottomrule
\end{tabular}
\caption{Chronological awareness sessions recorded through MorphicLedger v2 → GHX Visualizer pipeline.}
\end{table}
"""

    EXPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    header = (
        "\\section*{Appendix C — GHX Awareness Session Timeline}\n"
        "\\addcontentsline{toc}{section}{Appendix C — GHX Awareness Session Timeline}\n\n"
    )

    # ─── Smart header & dedup append mode ───────────────────────────────
    existing_runs = set()
    if EXPORT_FILE.exists():
        content = EXPORT_FILE.read_text(encoding="utf-8")
        # detect existing run IDs
        for line in content.splitlines():
            if "Run ID:" in line:
                rid = line.split("Run ID:")[-1].strip(" }")
                existing_runs.add(rid)
    else:
        content = ""

    # If this run already exists → skip
    if run_id in existing_runs:
        print(f"⚠️  {run_id} already present in appendix; skipping duplicate append.")
        return

    # Assemble content to append
    if not content.strip():
        # first creation
        new_content = header + tex_sub.strip() + "\n" + table_block.strip() + "\n"
        EXPORT_FILE.write_text(new_content, encoding="utf-8")
        print(f"[✓] Created Appendix C → {EXPORT_FILE}")
    else:
        # append only new run + refresh table
        cutoff = content.rfind(r"\subsection*{Session Summary}")
        if cutoff != -1:
            content = content[:cutoff].rstrip()
        with EXPORT_FILE.open("w", encoding="utf-8") as f:
            f.write(content + "\n\n" + tex_sub.strip() + "\n" + table_block.strip() + "\n")
        print(f"[➕] Appended new run → {run_id}")

    print(f"🧠 Latest Run ID: {run_id}")
    print(f"📁 Image Path:   {img_path}")
    print(f"🕒 Timestamp:    {ts_s}")

# ────────────────────────────────────────────────
#  Main entrypoint
# ────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 GHX Awareness → LaTeX Appendix Exporter (Phase 6.4b)")
    try:
        export_latest()
    except Exception as e:
        print(f"❌ Export failed: {e}")