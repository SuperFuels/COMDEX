"""
AION Fabric Stream Dashboard
────────────────────────────────────────────
Visual dashboard for monitoring live ψ̄-κ̄-σ-γ̄′ resonance tensors
received by the AION Fabric Stream Receiver.

Usage:
    PYTHONPATH=. python backend/AION/fabric/fabric_stream_dashboard.py
"""

import requests
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import datetime

# Receiver endpoint
FABRIC_ENDPOINT = "http://127.0.0.1:5090/fabric/all"

# Initialize dashboard app
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
app.title = "AION Fabric Stream Dashboard"

# ────────────────────────────────────────────────
# Layout definition
# ────────────────────────────────────────────────
app.layout = dbc.Container(
    [
        html.H2("🧠 AION Fabric Coherence + Feedback Dashboard", className="text-center mt-4 mb-4"),
        dcc.Graph(id="coherence-graph", style={"height": "70vh"}),

        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("σ - Coherence Stability"),
                            dbc.CardBody(html.H4(id="sigma-display", className="text-success")),
                        ],
                        color="dark", inverse=True, className="m-2"
                    ),
                    width=6,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("γ̄′ - Feedback Gain Mean"),
                            dbc.CardBody(html.H4(id="gamma-display", className="text-info")),
                        ],
                        color="dark", inverse=True, className="m-2"
                    ),
                    width=6,
                ),
            ],
            className="mb-3",
        ),

        dcc.Interval(id="update-interval", interval=2500, n_intervals=0),
        html.Div(id="status", className="text-center text-muted mt-2"),
    ],
    fluid=True,
)

# ────────────────────────────────────────────────
# Data Fetch + Plot Update
# ────────────────────────────────────────────────
@app.callback(
    [
        Output("coherence-graph", "figure"),
        Output("sigma-display", "children"),
        Output("gamma-display", "children"),
        Output("status", "children"),
    ],
    [Input("update-interval", "n_intervals")],
)
def update_dashboard(_):
    """Fetch live data from Fabric Receiver and update dashboard."""
    try:
        resp = requests.get(FABRIC_ENDPOINT, timeout=2)
        if resp.status_code != 200:
            raise Exception(f"Receiver returned {resp.status_code}")

        data = resp.json()
        if not data:
            return go.Figure(), "-", "-", "⏳ Waiting for data ..."

        timestamps = [
            datetime.datetime.fromtimestamp(d.get("timestamp")).strftime("%H:%M:%S")
            for d in data
        ]
        psi_vals = [d["tensor"].get("ψ̄", 0) for d in data]
        kappa_vals = [d["tensor"].get("κ̄", 0) for d in data]
        sigma_vals = [d["tensor"].get("σ", 0) for d in data]
        gamma_vals = [d["tensor"].get("γ̄′", 1.0) for d in data]

        # Build subplot: coherence (σ) + feedback gain (γ̄′)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=timestamps, y=sigma_vals, mode="lines+markers",
                                 name="σ (Stability Index)", line=dict(color="#00ff99", width=3)),
                      secondary_y=False)
        fig.add_trace(go.Scatter(x=timestamps, y=gamma_vals, mode="lines+markers",
                                 name="γ̄′ (Feedback Gain)", line=dict(color="#66ccff", width=2, dash="dot")),
                      secondary_y=True)
        fig.add_trace(go.Scatter(x=timestamps, y=psi_vals, mode="lines", name="ψ̄ (Cognitive Wave)",
                                 line=dict(color="#ffaa00", width=1, dash="dash")),
                      secondary_y=False)
        fig.add_trace(go.Scatter(x=timestamps, y=kappa_vals, mode="lines", name="κ̄ (Resonance Field)",
                                 line=dict(color="#ff66cc", width=1, dash="dash")),
                      secondary_y=False)

        fig.update_layout(
            template="plotly_dark",
            title="AION Fabric - Live Resonance Coherence (σ) vs Feedback Gain (γ̄′)",
            xaxis_title="Time",
            yaxis_title="Coherence (σ, ψ̄, κ̄)",
            legend_title="Tensor Metrics",
            margin=dict(l=40, r=40, t=60, b=40),
            yaxis_range=[0, 1.05],
            yaxis2=dict(title="Feedback Gain (γ̄′)", overlaying="y", side="right", range=[0.5, 2.0]),
        )

        sigma_current = f"{sigma_vals[-1]:.3f}"
        gamma_current = f"{gamma_vals[-1]:.3f}"
        status = f"✅ {len(data)} tensors streamed * σ={sigma_current} * γ̄′={gamma_current}"

        return fig, sigma_current, gamma_current, status

    except Exception as e:
        empty = go.Figure().update_layout(template="plotly_dark")
        return empty, "-", "-", f"⚠️ Stream error: {e}"


if __name__ == "__main__":
    print("📡 Launching AION Fabric Stream Dashboard at http://127.0.0.1:8050 ...")
    app.run_server(host="0.0.0.0", port=8050, debug=False)