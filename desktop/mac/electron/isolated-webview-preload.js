const { contextBridge, ipcRenderer } = require("electron");

const recorderBridge = {
  captureEvent(payload = {}) {
    ipcRenderer.sendToHost("aion-browser-recorder-event", payload);
  },

  capturedStep(payload = {}) {
    ipcRenderer.sendToHost("browser-operator-captured-step", payload);
  },
};

try {
  contextBridge.exposeInMainWorld("aionBrowserRecorder", recorderBridge);
} catch (_) {
  window.aionBrowserRecorder = recorderBridge;
}

console.log("[aion-webview-preload] loaded");
