// frontend/public/plugins/beam_highlighter.plugin.js
// ESM plugin module loaded by plugin_manager.loadFromUrl()
// Usage (in dev console):
//   window.SCI.loadPlugin('/plugins/beam_highlighter.plugin.js')

export default {
  id: "beam_highlighter",
  name: "Beam Highlighter",
  version: "0.1.0",

  // internal state
  _el: null,
  _last: 0,
  _threshold: 0.6,

  initialize() {
    console.log("[beam_highlighter] initialized");
  },

  /** Called each render frame if you forward ctx from your canvas loop. */
  onRenderFrame(ctx) {
    // ctx is whatever your app passes (commonly: { nodes, links, tick, ... })
    const now = Date.now();

    // Light periodic HUD stats update
    if (now - this._last > 250) {
      this._last = now;
      if (this._el) {
        const n = Array.isArray(ctx?.nodes) ? ctx.nodes.length : 0;
        const m = Array.isArray(ctx?.links) ? ctx.links.length : 0;
        const stats = this._el.querySelector(".bh-stats");
        if (stats) stats.textContent = `${n} nodes • ${m} links`;
      }
    }

    // Example effect: mark links with high SQI for your renderer to style
    if (Array.isArray(ctx?.links)) {
      for (const l of ctx.links) {
        if (typeof l.sqiScore === "number" && l.sqiScore >= this._threshold) {
          l.isHighlighted = true; // your Link renderer can check this
        }
      }
    }
  },

  /** Optional: react to generic app events routed via pluginManager.emit */
  onEvent(evt) {
    if (evt?.type === "set-threshold") {
      const v = Number(evt.payload);
      if (!Number.isNaN(v)) {
        this._threshold = v;
        console.log("[beam_highlighter] threshold ->", v);
      }
    }
  },

  /** Optional HUD panel. Returns an HTMLElement (PluginHUD will mount it). */
  renderHUD() {
    if (this._el) return this._el;

    const el = document.createElement("div");
    el.style.cssText =
      "position:absolute;right:12px;bottom:12px;background:rgba(17,17,17,.85);backdrop-filter:blur(6px);padding:10px 12px;border-radius:10px;color:#fff;font:12px system-ui;box-shadow:0 6px 18px rgba(0,0,0,.25);";

    el.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px">
        <span>🔆 Beam Highlighter</span>
        <span class="bh-stats" style="opacity:.8">–</span>
      </div>
      <div style="margin-top:8px;display:flex;align-items:center;gap:6px">
        <label style="opacity:.7">SQI ≥</label>
        <input class="bh-threshold" type="number" min="0" max="1" step="0.05"
               value="${this._threshold}"
               style="width:64px;padding:2px 6px;border-radius:6px;border:1px solid #444;background:#222;color:#fff">
      </div>
    `;

    el.querySelector(".bh-threshold").addEventListener("input", (e) => {
      const v = Number(e.target.value);
      if (!Number.isNaN(v)) this._threshold = v;
    });

    this._el = el;
    return el;
  },

  dispose() {
    console.log("[beam_highlighter] disposed");
    if (this._el?.parentNode) this._el.parentNode.removeChild(this._el);
    this._el = null;
  },
};