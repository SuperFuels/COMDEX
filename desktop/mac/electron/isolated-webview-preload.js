const { ipcRenderer } = require("electron");

window.aionBrowserRecorder = {
  captureEvent(payload = {}) {
    ipcRenderer.sendToHost("aion-browser-recorder-event", payload);
  },

  capturedStep(payload = {}) {
    ipcRenderer.sendToHost("browser-operator-captured-step", payload);
  },
};

console.log("[aion-webview-preload] loaded");
