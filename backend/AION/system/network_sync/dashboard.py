"""
AION Resonant Ledger Dashboard (E5.3)
────────────────────────────────────────────
Visual dashboard for monitoring Δφ (phase drift) and Δσ (stability deviation)
in the AION ↔ QQC Resonant Network. Reads state snapshots written by the
orchestrator (`resonance_sync_state.json`) and displays live coherence graphs.

Run:
    PYTHONPATH=. python backend/AION/system/network_sync/dashboard.py

────────────────────────────────────────────
Features:
• Auto-refreshes every few seconds
• Plots Δφ and Δσ evolution for each node
• Shows node role, last-seen time, and phase energy
• Detects drift threshold crossings visually
────────────────────────────────────────────
"""

import os
import json
import time
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import threading
import logging

# ───────────────────────────────────────────────
# Config
# ───────────────────────────────────────────────
STATE_FILE = "backend/logs/resonance_sync_state.json"
REFRESH_INTERVAL_MS = 2000
PHASE_THRESHOLD = 0.05

os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
logger = logging.getLogger("ResonantDashboard")
logger.setLevel(logging.INFO)
logging.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s")

def safe_read_json(path):
    """Safely read JSON even if file is partially written."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
            # try to recover from multiple JSON blobs concatenated
            if "}\n{" in data:
                data = "[" + data.replace("}\n{", "},{") + "]"
                parsed = json.loads(data)[-1]  # use most recent
            else:
                parsed = json.loads(data)
            return parsed
    except Exception as e:
        print(f"[WARNING] Failed to read state safely: {e}")
        return {}

# ───────────────────────────────────────────────
# Utility — Load state file
# ───────────────────────────────────────────────
# ───────────────────────────────────────────────
# Utility — Load state file (safe concurrent read)
# ───────────────────────────────────────────────
def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    state_data = safe_read_json(STATE_FILE)
    if not state_data:
        logger.warning("⚠️ State file empty or unreadable, returning {}")
    return state_data

# ───────────────────────────────────────────────
# In-memory buffers
# ───────────────────────────────────────────────
state_history = {}  # node_id → list of {time, Δφ, Δσ}

def append_state(snapshot):
    now = time.time()
    for nid, metrics in snapshot.items():
        Δφ = metrics.get("Δφ", 0)
        Δσ = metrics.get("Δσ", 0)
        if nid not in state_history:
            state_history[nid] = []
        state_history[nid].append({
            "t": now,
            "Δφ": Δφ,
            "Δσ": Δσ,
        })
        # trim to last 200 points
        if len(state_history[nid]) > 200:
            state_history[nid] = state_history[nid][-200:]

# ───────────────────────────────────────────────
# Dash App
# ───────────────────────────────────────────────
app = dash.Dash(__name__)
app.title = "AION Resonant Ledger Dashboard"

app.layout = html.Div([
    html.H1("AION ↔ QQC Resonant Coherence Monitor", style={"textAlign": "center"}),
    html.Div(id="summary-table"),
    dcc.Graph(id="phase-graph"),
    dcc.Graph(id="stability-graph"),
    dcc.Interval(id="update-interval", interval=REFRESH_INTERVAL_MS, n_intervals=0),
])

# ───────────────────────────────────────────────
# Update callback
# ───────────────────────────────────────────────
@app.callback(
    [Output("summary-table", "children"),
     Output("phase-graph", "figure"),
     Output("stability-graph", "figure")],
    [Input("update-interval", "n_intervals")]
)
def update_dashboard(n):
    snapshot = load_state()
    if not snapshot:
        return html.P("Waiting for sync data..."), go.Figure(), go.Figure()

    append_state(snapshot)

    # Build summary table
    rows = []
    for nid, data in snapshot.items():
        rows.append(html.Tr([
            html.Td(nid),
            html.Td(data.get("role", "")),
            html.Td(f"{data.get('phi', 0):.3f}"),
            html.Td(f"{data.get('Δφ', 0):.3f}"),
            html.Td(f"{data.get('Δσ', 0):.3f}"),
            html.Td(f"{data.get('age', 0):.2f}s ago"),
        ]))
    table = html.Table(
        [html.Tr([html.Th("Node"), html.Th("Role"), html.Th("φ"), html.Th("Δφ"), html.Th("Δσ"), html.Th("Last Seen")])] + rows,
        style={
            "width": "80%",
            "margin": "auto",
            "textAlign": "center",
            "border": "1px solid #333",
            "borderCollapse": "collapse",
        }
    )

    # Plot Δφ over time
    phase_fig = go.Figure()
    for nid, history in state_history.items():
        xs = [p["t"] for p in history]
        ys = [p["Δφ"] for p in history]
        phase_fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers", name=f"{nid} Δφ"
        ))
    phase_fig.add_hline(y=PHASE_THRESHOLD, line_dash="dash", line_color="red", annotation_text="Δφ threshold")
    phase_fig.update_layout(
        title="Phase Drift Δφ Over Time",
        xaxis_title="Time",
        yaxis_title="Δφ",
        height=400,
        template="plotly_dark"
    )

    # Plot Δσ over time
    stability_fig = go.Figure()
    for nid, history in state_history.items():
        xs = [p["t"] for p in history]
        ys = [p["Δσ"] for p in history]
        stability_fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers", name=f"{nid} Δσ"
        ))
    stability_fig.update_layout(
        title="Stability Deviation Δσ Over Time",
        xaxis_title="Time",
        yaxis_title="Δσ",
        height=400,
        template="plotly_dark"
    )

    return table, phase_fig, stability_fig

# ───────────────────────────────────────────────
# Run
# ───────────────────────────────────────────────
if __name__ == "__main__":
    import os
    port = int(os.getenv("DASH_PORT", "8050"))
    logger.info(f"🚀 Starting Resonant Ledger Dashboard on http://127.0.0.1:{port}")
    app.run_server(host="0.0.0.0", port=port, debug=False)