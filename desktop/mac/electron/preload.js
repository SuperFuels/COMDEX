const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("aionDesktop", {
  onBackendStatus(callback) {
    if (typeof callback !== "function") return () => {};

    const listener = (_event, payload) => {
      callback(payload);
    };

    ipcRenderer.on("backend-status", listener);

    return () => {
      ipcRenderer.removeListener("backend-status", listener);
    };
  },

  async getBackendStatus() {
    return await ipcRenderer.invoke("desktop-backend-status");
  },

  async restartBackend() {
    return await ipcRenderer.invoke("desktop-backend-restart");
  },

  async getRuntimeInfo() {
    return await ipcRenderer.invoke("desktop-runtime-info");
  },

  async getSecuritySentinelStatus() {
    return await ipcRenderer.invoke("aion-security-sentinel-status");
  },

  async openSecuritySentinel() {
    return await ipcRenderer.invoke("aion-security-sentinel-open");
  },

  onOpenCybersecurity(callback) {
    if (typeof callback !== "function") return () => {};
    const listener = () => callback();
    ipcRenderer.on("aion-open-cybersecurity", listener);
    return () => ipcRenderer.removeListener("aion-open-cybersecurity", listener);
  },

  async signAionFlowRequest(payload = {}) {
    return await ipcRenderer.invoke("aion-flow-sign-request", payload);
  },

  async listCustomDepartments(payload = {}) {
    return await ipcRenderer.invoke("aion-custom-departments-list", payload);
  },

  async getPilotStatus() {
    return await ipcRenderer.invoke("pilot-control-status");
  },

  async openPilotDashboard() {
    return await ipcRenderer.invoke("pilot-open-dashboard");
  },

  async runPilotControl(action = "") {
    return await ipcRenderer.invoke("pilot-control-action", action);
  },

  async openExternalUrl(url = "") {
    return await ipcRenderer.invoke("aion-open-external-url", url);
  },

  async openBusinessArtifact(storagePath = "") {
    return await ipcRenderer.invoke("aion-open-business-artifact", storagePath);
  },

  async chooseLocalVideo() {
    return await ipcRenderer.invoke("aion-choose-local-video");
  },

  async chooseLocalMedia(payload = {}) {
    return await ipcRenderer.invoke("aion-choose-local-media", payload);
  },

  async chooseChatAttachments() {
    return await ipcRenderer.invoke("aion-choose-chat-attachments");
  },

  async playLocalVoice(payload = {}) {
    return await ipcRenderer.invoke("aion-play-local-voice", payload);
  },

  async playSystemVoice(payload = {}) {
    return await ipcRenderer.invoke("aion-play-system-voice", payload);
  },

  async requestMicrophonePermission() {
    return await ipcRenderer.invoke("aion-request-microphone-permission");
  },

  async launchSpatialBoardroom(payload = {}) {
    return await ipcRenderer.invoke("aion-launch-spatial-boardroom", payload);
  },

  async getSpatialBoardroomEmbed(payload = {}) {
    return await ipcRenderer.invoke("aion-spatial-boardroom-embed", payload);
  },

  async sendSpatialBoardroomEvent(payload = {}) {
    return await ipcRenderer.invoke("aion-spatial-boardroom-event", payload);
  },

  onSpatialBoardroomAction(callback) {
    if (typeof callback !== "function") return () => {};
    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on("aion-spatial-boardroom-action", listener);
    return () => ipcRenderer.removeListener("aion-spatial-boardroom-action", listener);
  },

  /**
   * Existing isolated browser bridge.
   * Keep this because your current Electron main may already use it.
   */
  async openIsolatedBrowser(payload = {}) {
    return await ipcRenderer.invoke("aion-open-isolated-browser", payload);
  },

  async startBrowserRecording() {
    return await ipcRenderer.invoke("aion-start-browser-recording");
  },

  async stopBrowserRecording() {
    return await ipcRenderer.invoke("aion-stop-browser-recording");
  },

  async replayBrowserSkill(payload = {}) {
    return await ipcRenderer.invoke("aion-replay-browser-skill", payload);
  },

  async executeGovernedBrowserPlan(payload = {}) {
    return await ipcRenderer.invoke("aion-execute-governed-browser-plan", payload);
  },

  async executeGovernedComputerPlan(payload = {}) {
    return await ipcRenderer.invoke("aion-execute-governed-computer-plan", payload);
  },

  async getDesktopPermissionSetupStatus() {
    return await ipcRenderer.invoke("aion-desktop-permissions-status");
  },

  async prepareDesktopPermissions() {
    return await ipcRenderer.invoke("aion-desktop-permissions-prepare");
  },

  onBrowserRecorderEvent(callback) {
    if (typeof callback !== "function") return () => {};

    const listener = (_event, payload) => {
      callback(payload);
    };

    ipcRenderer.on("browser-recorder-event", listener);

    return () => {
      ipcRenderer.removeListener("browser-recorder-event", listener);
    };
  },

  notifyIsolatedBrowserLoaded(payload = {}) {
    ipcRenderer.send("aion-isolated-browser-loaded", payload);
  },

  forwardBrowserRecorderEvent(payload = {}) {
    ipcRenderer.send("aion-browser-recorder-event", payload);
  },

  /**
   * Phase 4C.2 point-and-click capture bridge.
   * These are the newer, explicit browser-operator channels.
   */
  async openBrowserOperatorIsolatedBrowser(payload = {}) {
    return await ipcRenderer.invoke(
      "aion-open-isolated-browser",
      payload,
    );
  },

  async startCaptureNextClick(payload = {}) {
    return await ipcRenderer.invoke(
      "aion-start-capture-next-click",
      payload,
    );
  },

  onBrowserCapturedStep(callback) {
    if (typeof callback !== "function") return () => {};

    const listener = (_event, payload) => {
      callback(payload);
    };

    ipcRenderer.on("browser-operator-captured-step", listener);

    return () => {
      ipcRenderer.removeListener("browser-operator-captured-step", listener);
    };
  },
});

contextBridge.exposeInMainWorld("aionBrowserRecorder", {
  captureEvent(payload = {}) {
    ipcRenderer.send("aion-browser-recorder-event", payload);
  },

  capturedStep(payload = {}) {
    ipcRenderer.send("browser-operator-captured-step-from-page", payload);
  },
});
