# File: backend/routes/aion_brain.py
# 🧠 AION Brain Dashboard — Real-time Φ-Telemetry + Personality & Memory Visualizer

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/brain", response_class=HTMLResponse)
async def aion_brain_dashboard():
    """
    Live AION Brain dashboard.
    Streams Φ-coherence, entropy, flux, reasoning, and personality updates in real time.
    Adds the Resonance Memory Timeline panel and dynamic Lexicon viewer.
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
        h1 { color: #58a6ff; font-size: 1.8em; margin-bottom: 0; }
        p { color: #8b949e; margin-top: 6px; }

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
          height: fit-content;
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

        /* 🧠 Timeline Styles */
        .timeline {
          background: #161b22;
          border-radius: 8px;
          padding: 16px;
          width: 95%;
          max-width: 1100px;
          height: 260px;
          overflow-y: auto;
          box-shadow: 0 0 10px rgba(0,0,0,0.5);
        }
        .timeline-entry {
          padding: 8px;
          border-bottom: 1px solid #30363d;
          font-size: 0.92em;
        }
        .timeline-entry:last-child { border-bottom: none; }
        .timeline-time { color: #8b949e; font-size: 0.8em; }
        .timeline-msg { margin-top: 4px; }
        .tone-harmonic { color: #3fb950; }
        .tone-stable { color: #58a6ff; }
        .tone-chaotic { color: #f85149; }
        .tone-dispersed { color: #ffb347; }
        .tone-neutral { color: #c9d1d9; }
      </style>
    </head>
    <body>
      <header>
        <h1>🧠 AION Brain — Φ-Field Telemetry</h1>
        <p>Live coherence, entropy, flux, personality feedback, and memory timeline</p>
      </header>

      <div class="dashboard">
        <canvas id="phiChart" width="720" height="360"></canvas>

        <div class="panel" id="personalityPanel">
          <h2>🧬 Personality Profile</h2>
          <div id="traits"></div>
          <div class="reasoning" id="reasoningInfo">Awaiting resonance...</div>
        </div>
      </div>

      <div class="timeline" id="timeline">
        <h2>📜 Resonance Memory Timeline</h2>
      </div>

      <div class="panel" id="lexiconPanel" style="width:95%;max-width:1100px;margin-top:20px;">
        <h2>📚 Resonance Lexicon</h2>
        <table id="lexiconTable" style="width:100%;border-collapse:collapse;">
          <thead>
            <tr style="color:#8b949e;border-bottom:1px solid #30363d;">
              <th align="left">Keyword</th>
              <th align="right">Φ_load</th>
              <th align="right">Φ_flux</th>
              <th align="right">Φ_entropy</th>
              <th align="right">Φ_coherence</th>
              <th align="left">Tone</th>
            </tr>
          </thead>
          <tbody id="lexiconBody"></tbody>
        </table>
      </div>
      <div class="panel" id="graphPanel" style="width:95%;max-width:1100px;margin-top:20px;">
        <h2>🕸️ Φ-Knowledge Graph</h2>
        <canvas id="graphCanvas" width="900" height="500"></canvas>
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
            scales: { y: { min: 0, max: 1 }, x: { display: false } },
            plugins: { legend: { labels: { color: '#c9d1d9' } } }
          }
        });

        let reconnectDelay = 1000;
        const timeline = document.getElementById("timeline");

        function addTimelineEntry(state) {
          const tone = state.reasoning?.emotion || "neutral";
          const ts = new Date().toLocaleTimeString();
          const entry = document.createElement("div");
          entry.className = "timeline-entry tone-" + tone;
          entry.innerHTML = `
            <div class="timeline-time">${ts}</div>
            <div class="timeline-msg">
              <strong>${tone.toUpperCase()}</strong> — coherence=${(state["Φ_coherence"]||0).toFixed(3)}, entropy=${(state["Φ_entropy"]||0).toFixed(3)}
            </div>
          `;
          timeline.appendChild(entry);
          timeline.scrollTop = timeline.scrollHeight;
          if (timeline.children.length > 50) timeline.removeChild(timeline.children[1]);
        }

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

            addTimelineEntry(state);

            if (state.reasoning) {
              document.getElementById("reasoningInfo").innerText =
                `Emotion: ${state.reasoning.emotion} | Intention: ${state.reasoning.intention}`;
            }

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

        // --- 📚 Lexicon Viewer ----------------------------------------------------
        async function refreshLexicon() {
          const resp = await fetch('/api/aion/lexicon');
          const js = await resp.json();
          const tbody = document.getElementById('lexiconBody');
          tbody.innerHTML = '';
          for (const [word, vec] of Object.entries(js.lexicon || {})) {
            const tone =
              vec["Φ_coherence"] > 0.85 && vec["Φ_entropy"] < 0.3 ? "harmonic" :
              vec["Φ_coherence"] > 0.7 && vec["Φ_entropy"] < 0.5 ? "stable" :
              vec["Φ_entropy"] > 0.7 ? "chaotic" :
              vec["Φ_coherence"] < 0.4 ? "dispersed" : "neutral";

            tbody.innerHTML += `
              <tr class="tone-${tone}">
                <td>${word}</td>
                <td align="right">${vec["Φ_load"].toFixed(3)}</td>
                <td align="right">${vec["Φ_flux"].toFixed(3)}</td>
                <td align="right">${vec["Φ_entropy"].toFixed(3)}</td>
                <td align="right">${vec["Φ_coherence"].toFixed(3)}</td>
                <td>${tone}</td>
              </tr>`;
          }
        }

        setInterval(refreshLexicon, 5000);
        refreshLexicon();
        connectWS();
        // --- 🕸️ Φ-Graph Visualizer ---------------------------------------------
        async function drawGraph() {
        const resp = await fetch('/api/aion/graph');
        const js = await resp.json();
        const canvas = document.getElementById('graphCanvas');
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const nodes = Object.entries(js.nodes || {});
        const edges = Object.entries(js.edges || {});

        const pos = {};
        const radius = 200;
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        const step = (2 * Math.PI) / Math.max(1, nodes.length);

        nodes.forEach(([term, node], i) => {
            const x = cx + radius * Math.cos(i * step);
            const y = cy + radius * Math.sin(i * step);
            pos[term] = { x, y };
        });

        // Draw edges
        ctx.strokeStyle = '#30363d';
        ctx.lineWidth = 1;
        for (const [key, edge] of edges) {
            const [a, b] = key.split('↔');
            if (pos[a] && pos[b]) {
            const s = pos[a], t = pos[b];
            const strength = edge.strength || 0.5;
            ctx.strokeStyle =
                strength > 0.7 ? '#3fb950' :
                strength > 0.5 ? '#58a6ff' :
                strength > 0.3 ? '#f85149' : '#8b949e';
            ctx.beginPath();
            ctx.moveTo(s.x, s.y);
            ctx.lineTo(t.x, t.y);
            ctx.stroke();
            }
        }

        // Draw nodes
        for (const [term, node] of nodes) {
            const { x, y } = pos[term];
            const coh = node["Φ_coherence"] || 0.5;
            const size = 6 + coh * 8;
            ctx.beginPath();
            ctx.arc(x, y, size, 0, 2 * Math.PI);
            ctx.fillStyle = coh > 0.8 ? '#3fb950' : coh > 0.6 ? '#58a6ff' : '#f85149';
            ctx.fill();
            ctx.fillStyle = '#c9d1d9';
            ctx.font = '12px system-ui';
            ctx.textAlign = 'center';
            ctx.fillText(term, x, y - size - 6);
        }
        }
        setInterval(drawGraph, 4000);
        drawGraph();
      </script>

      <!-- 🧠 Φ Reinforcement Monitor -->
      <div class="panel" id="reinforcePanel" style="width:95%;max-width:1100px;margin-top:20px;">
        <h2>⚖️ Φ Reinforcement Monitor</h2>
        <div id="reinforceStats" style="font-size:0.95em;color:#8b949e;">
          Loading reinforcement data...
        </div>
        <canvas id="reinforceChart" width="900" height="280" style="margin-top:10px;"></canvas>
      </div>

      <script>
        const rctx = document.getElementById('reinforceChart').getContext('2d');
        const reinforceChart = new Chart(rctx, {
          type: 'bar',
          data: {
            labels: ['Φ_load','Φ_flux','Φ_entropy','Φ_coherence'],
            datasets: [{
              label: 'Δ (Change)',
              backgroundColor: ['#f85149','#3fb950','#ffb347','#58a6ff'],
              data: [0,0,0,0]
            }]
          },
          options: {
            scales: {
              y: { min: -0.2, max: 0.2, ticks: { color: '#c9d1d9' } },
              x: { ticks: { color: '#c9d1d9' } }
            },
            plugins: { legend: { labels: { color: '#c9d1d9' } } }
          }
        });

        let lastBaseline = null;

        async function refreshReinforce() {
          try {
            // 🔁 Trigger reinforcement recalculation first
            await fetch('/api/aion/reinforce', { method: 'POST' });

            // 🔎 Then pull latest baseline
            const resp = await fetch('/api/aion/reinforce');
            const js = await resp.json();
            if (!js.baseline) return;

            const b = js.baseline;
            document.getElementById('reinforceStats').innerHTML = `
              Φ_load=${b["Φ_load"].toFixed(4)} |
              Φ_flux=${b["Φ_flux"].toFixed(4)} |
              Φ_entropy=${b["Φ_entropy"].toFixed(4)} |
              Φ_coherence=${b["Φ_coherence"].toFixed(4)} <br>
              stability=${(b.beliefs.stability*100).toFixed(1)}% |
              trust=${(b.beliefs.trust*100).toFixed(1)}% |
              clarity=${(b.beliefs.clarity*100).toFixed(1)}% |
              curiosity=${(b.beliefs.curiosity*100).toFixed(1)}%
            `;

            if (lastBaseline) {
              const deltas = [
                b["Φ_load"] - lastBaseline["Φ_load"],
                b["Φ_flux"] - lastBaseline["Φ_flux"],
                b["Φ_entropy"] - lastBaseline["Φ_entropy"],
                b["Φ_coherence"] - lastBaseline["Φ_coherence"]
              ];
              reinforceChart.data.datasets[0].data = deltas;
              reinforceChart.update();
            }
            lastBaseline = b;
          } catch (err) {
            console.warn('Reinforce poll failed', err);
          }
        }

        setInterval(refreshReinforce, 6000);
        refreshReinforce();
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)