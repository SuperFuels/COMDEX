"""
AION Fabric Stream Dashboard
────────────────────────────────────────────
Visual dashboard for monitoring live ψ̄–κ̄–σ resonance tensors
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

# Receiver endpoint
FABRIC_ENDPOINT = "http://127.0.0.1:5090/fabric/all"

# Initialize dashboard app
app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])
app.title = "AION Fabric Stream Dashboard"

# Layout definition
app.layout = dbc.Container(
    [
        html.H2("🧠 AION Fabric Coherence Dashboard", className="text-center mt-4 mb-4"),
        dcc.Graph(id="coherence-graph", style={"height": "70vh"}),
        dcc.Interval(id="update-interval", interval=2500, n_intervals=0),
        html.Div(id="status", className="text-center text-muted mt-2"),
    ],
    fluid=True,
)


@app.callback(
    [Output("coherence-graph", "figure"), Output("status", "children")],
    [Input("update-interval", "n_intervals")],
)
def update_dashboard(_):
    """Fetch data from Fabric Receiver and update live plot."""
    try:
        resp = requests.get(FABRIC_ENDPOINT, timeout=2)
        if resp.status_code != 200:
            raise Exception(f"Receiver returned {resp.status_code}")

        data = resp.json()
        if not data:
            return go.Figure(), "⏳ Waiting for data …"

        # Parse stream data
        timestamps = [d.get("timestamp") for d in data]
        psi_vals = [d["tensor"].get("ψ̄", 0) for d in data]
        kappa_vals = [d["tensor"].get("κ̄", 0) for d in data]
        sigma_vals = [d["tensor"].get("σ", 0) for d in data]

        fig = make_subplots(rows=1, cols=1)
        fig.add_trace(go.Scatter(x=timestamps, y=psi_vals, mode="lines+markers",
                                 name="ψ̄ (Cognitive Wave)"))
        fig.add_trace(go.Scatter(x=timestamps, y=kappa_vals, mode="lines+markers",
                                 name="κ̄ (Resonance Field)"))
        fig.add_trace(go.Scatter(x=timestamps, y=sigma_vals, mode="lines+markers",
                                 name="σ (Stability Index)"))

        fig.update_layout(
            template="plotly_dark",
            xaxis_title="Time",
            yaxis_title="Value",
            legend_title="Tensor Components",
            margin=dict(l=40, r=20, t=40, b=40),
            yaxis_range=[0, 1.05],
        )

        status = f"✅ Last update: {len(data)} tensors streamed"
        return fig, status

    except Exception as e:
        empty = go.Figure().update_layout(template="plotly_dark")
        return empty, f"⚠️ Stream error: {e}"


if __name__ == "__main__":
    print("📡 Launching AION Fabric Stream Dashboard at http://127.0.0.1:8050 …")
    app.run_server(host="0.0.0.0", port=8050, debug=False)