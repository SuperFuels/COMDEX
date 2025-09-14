// Minimal ESM plugin example.
// Load via:  window.SCI.loadPlugin('/plugins/beam_highlighter.plugin.js')

const plugin = {
  id: "beam-highlighter",
  name: "Beam Highlighter",
  version: "0.1.0",

  initialize() {
    console.log("[beam-highlighter] initialized");
  },

  onRenderFrame(ctx) {
    // Example: log graph size every ~2s
    const t = Date.now();
    if (!this._last || t - this._last > 2000) {
      this._last = t;
      const n = (ctx.nodes && ctx.nodes.length) || 0;
      const m = (ctx.links && ctx.links.length) || 0;
      console.log(`[beam-highlighter] frame: nodes=${n} links=${m}`);
    }
  },

  // Optional HUD panel:
  renderHUD() {
    const el = document.createElement("div");
    el.textContent = "Beam Highlighter: active";
    el.style.cssText = "position:absolute;right:12px;bottom:12px;background:#1119;padding:8px 12px;border-radius:8px;color:#fff;font:12px system-ui;";
    return el; // simple DOM node is fine (React will mount it)
  },

  dispose() {
    console.log("[beam-highlighter] disposed");
  },
};

export default plugin;