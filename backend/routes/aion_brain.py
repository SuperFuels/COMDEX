# File: backend/routes/aion_brain.py
# 🧠 AION Brain Dashboard — Real-time Φ-Telemetry + Personality Visualizer

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/brain", response_class=HTMLResponse)
async def aion_brain_dashboard():
    """
    Live AION Brain dashboard.
    Streams Φ-coherence, entropy, flux, reasoning, and personality updates in real time.
    Connects to /api/aion/phi-stream and /api/aion/phi-state.
    """
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>AION 🧠 Brain Telemetry</title>
      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
      <style>
        body {
          background: #0d1117;
          color: #c9d1d9;
          font-family: system-ui, sans-serif;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        header {
          text-align: center;
          padding: 16px 0;
        }
        h1 {
          color: #58a6ff;
          font-size: 1.8em;
        }
        .dashboard {
          display: flex;
          gap: 20px;
          flex-wrap: wrap;
          justify-content: center;
          margin-bottom: 30px;
        }
        canvas {
          background: #161b22;
          border-radius: 8px;
          margin-top: 10px;
          box-shadow: 0 0 10px rgba(88,166,255,0.2);
        }
        .panel {
          background: #161b22;
          border-radius: 8px;
          padding: 16px;
          min-width: 280px;
          max-width: 340px;
          box-shadow: 0 0 10px rgba(0,0,0,0.4);
        }
        .panel h2 {
          color: #58a6ff;
          font-size: 1.1em;
          margin-bottom: 10px;
          border-bottom: 1px solid #30363d;
          padding-bottom: 4px;
        }
        .trait {
          display: flex;
          justify-content: space-between;
          margin-bottom: 6px;
        }
        .trait-bar {
          height: 6px;
          background: #30363d;
          border-radius: 4px;
          overflow: hidden;
          width: 100%;
          margin-left: 10px;
        }
        .trait-fill {
          height: 100%;
          background: linear-gradient(90deg, #58a6ff, #3fb950);
        }
        .reasoning {
          font-size: 0.9em;
          color: #8b949e;
          margin-top: 8px;
        }
      </style>
    </head>
    <body>
      <header>
        <h1>🧠 AION Brain — Φ-Field Telemetry</h1>
        <p>Live coherence, entropy, and flux readings + personality adaptation feedback</p>
      </header>

      <div class="dashboard">
        <canvas id="phiChart" width="720" height="360"></canvas>

        <div class="panel" id="personalityPanel">
          <h2>🧬 Personality Profile</h2>
          <div id="traits"></div>
          <div class="reasoning" id="reasoningInfo">Awaiting resonance...</div>
        </div>
      </div>

      <script>
        const ctx = document.getElementById('phiChart').getContext('2d');
        const chart = new Chart(ctx, {
          type: 'line',
          data: {
            labels: [],
            datasets: [
              { label: 'Φ_coherence', borderColor: '#58a6ff', data: [], fill: false },
              { label: 'Φ_entropy', borderColor: '#f85149', data: [], fill: false },
              { label: 'Φ_flux', borderColor: '#3fb950', data: [], fill: false }
            ]
          },
          options: {
            animation: false,
            scales: {
              y: { min: 0, max: 1 },
              x: { display: false }
            },
            plugins: { legend: { labels: { color: '#c9d1d9' } } }
          }
        });

        // 🔄 Auto-reconnect WebSocket with exponential backoff
        let reconnectDelay = 1000;
        function connectWS() {
          const ws = new WebSocket(`ws://${location.host}/api/aion/phi-stream`);

          ws.onmessage = async (event) => {
            const data = JSON.parse(event.data);
            const state = data.state;
            const label = new Date().toLocaleTimeString();

            if (chart.data.labels.length > 50) {
              chart.data.labels.shift();
              chart.data.datasets.forEach(ds => ds.data.shift());
            }

            chart.data.labels.push(label);
            chart.data.datasets[0].data.push(state["Φ_coherence"]);
            chart.data.datasets[1].data.push(state["Φ_entropy"]);
            chart.data.datasets[2].data.push(state["Φ_flux"]);
            chart.update();

            // Update reasoning panel (if any)
            if (state.reasoning) {
              document.getElementById("reasoningInfo").innerText =
                `Emotion: ${state.reasoning.emotion} | Intention: ${state.reasoning.intention}`;
            }

            // Fetch personality state every few updates
            if (Math.random() < 0.2) {
              const resp = await fetch('/api/aion/phi-state');
              const js = await resp.json();
              if (js.phi_state && js.phi_state.personality) {
                updateTraits(js.phi_state.personality);
              }
            }
          };

          ws.onclose = () => {
            console.warn("Φ-stream disconnected, retrying...");
            setTimeout(connectWS, reconnectDelay);
            reconnectDelay = Math.min(reconnectDelay * 1.5, 10000);
          };

          ws.onopen = () => {
            reconnectDelay = 1000;
            console.log("Φ-stream connected");
          };
        }

        function updateTraits(personality) {
          const traitsDiv = document.getElementById("traits");
          traitsDiv.innerHTML = "";
          for (const [name, value] of Object.entries(personality)) {
            const percent = Math.round(value * 100);
            traitsDiv.innerHTML += `
              <div class="trait">
                <span>${name}</span>
                <div class="trait-bar">
                  <div class="trait-fill" style="width:${percent}%;"></div>
                </div>
                <span>${percent}%</span>
              </div>
            `;
          }
        }

        connectWS();
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)