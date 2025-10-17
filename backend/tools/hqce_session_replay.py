# ──────────────────────────────────────────────
#  Tessaris • HQCE Session Replay Engine (Stage 12)
#  Reconstruct ψ–κ–T–C field evolution over time
#  Uses stored MorphicLedger / TelemetryDB records
# ──────────────────────────────────────────────

import os
import time
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional

import plotly.graph_objs as go
from plotly.subplots import make_subplots

from backend.modules.holograms.hqce_telemetry_db import hqce_telemetry_db
from backend.modules.holograms.morphic_ledger import morphic_ledger

logger = logging.getLogger(__name__)


class HQCESessionReplay:
    """
    Loads telemetry or ledger data, generates temporal frames,
    and replays ψ–κ–T–C field evolution with adjustable speed.
    """

    def __init__(self, source: str = "db", session_id: Optional[str] = None):
        """
        :param source: "db" or path to JSONL ledger.
        :param session_id: optional filter for DB mode.
        """
        self.source = source
        self.session_id = session_id
        self.records: List[Dict[str, Any]] = []

    # ──────────────────────────────────────────────
    #  Data Loading
    # ──────────────────────────────────────────────
    def load_records(self):
        """Load all telemetry records from the selected source."""
        if self.source == "db":
            cur = hqce_telemetry_db.conn.cursor()
            query = "SELECT timestamp, psi, kappa, T, coherence, stability FROM telemetry"
            if self.session_id:
                query += " WHERE session_id=?"
                cur.execute(query, (self.session_id,))
            else:
                cur.execute(query)
            rows = cur.fetchall()
            self.records = [
                {"timestamp": r[0], "psi": r[1], "kappa": r[2],
                 "T": r[3], "coherence": r[4], "stability": r[5]}
                for r in rows
            ]
        elif os.path.exists(self.source):
            self.records = morphic_ledger.load_all()
        else:
            raise FileNotFoundError(f"No telemetry source found: {self.source}")

        self.records.sort(key=lambda r: r["timestamp"])
        logger.info(f"[HQCESessionReplay] Loaded {len(self.records)} records.")

    # ──────────────────────────────────────────────
    #  Replay Loop
    # ──────────────────────────────────────────────
    async def replay(self, interval: float = 0.5):
        """Animate ψ–κ–T–C over time in terminal + Plotly graph."""
        if not self.records:
            self.load_records()

        timestamps = [r["timestamp"] for r in self.records]
        ψ_vals = [r["psi"] for r in self.records]
        κ_vals = [r["kappa"] for r in self.records]
        T_vals = [r["T"] for r in self.records]
        C_vals = [r["coherence"] for r in self.records]

        print("\n🧠 HQCE Session Replay — ψ–κ–T–C Evolution\n")
        for i, r in enumerate(self.records):
            print(f"[{i+1:03}/{len(self.records)}] "
                  f"ψ={r['psi']:.3f} κ={r['kappa']:.3f} "
                  f"T={r['T']:.3f} C={r['coherence']:.3f}  "
                  f"S={r['stability']:.3f}")
            await asyncio.sleep(interval)

        # Plot final time-series
        fig = make_subplots(rows=2, cols=2,
                            subplot_titles=("ψ", "κ", "T", "C"))
        fig.add_trace(go.Scatter(x=timestamps, y=ψ_vals, name="ψ", mode="lines"), 1, 1)
        fig.add_trace(go.Scatter(x=timestamps, y=κ_vals, name="κ", mode="lines"), 1, 2)
        fig.add_trace(go.Scatter(x=timestamps, y=T_vals, name="T", mode="lines"), 2, 1)
        fig.add_trace(go.Scatter(x=timestamps, y=C_vals, name="C", mode="lines"), 2, 2)
        fig.update_layout(height=800, title_text="HQCE ψ–κ–T–C Replay (Temporal Evolution)")
        fig.show()

    # ──────────────────────────────────────────────
    #  Export Replay Frames
    # ──────────────────────────────────────────────
    def export_frames(self, out_dir: str = "outputs/hqce_replay_frames") -> List[str]:
        """Save individual time-step frames as JSON files."""
        os.makedirs(out_dir, exist_ok=True)
        paths = []
        for i, rec in enumerate(self.records):
            path = os.path.join(out_dir, f"frame_{i:04}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(rec, f, indent=2)
            paths.append(path)
        logger.info(f"[HQCESessionReplay] Exported {len(paths)} frames → {out_dir}")
        return paths


# ──────────────────────────────────────────────
#  CLI Entry
# ──────────────────────────────────────────────
def run_replay(source: str = "db", speed: float = 0.5):
    replay = HQCESessionReplay(source)
    replay.load_records()
    asyncio.run(replay.replay(interval=speed))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run HQCE Session Replay Engine")
    parser.add_argument("--source", default="db", help="Source: 'db' or path to ledger.jsonl")
    parser.add_argument("--speed", type=float, default=0.5, help="Delay (s) between frames")
    args = parser.parse_args()
    run_replay(args.source, args.speed)