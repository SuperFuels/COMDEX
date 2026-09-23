const {
  app,
  BrowserWindow,
  ipcMain,
  globalShortcut,
  Menu,
  session,
  shell,
  systemPreferences,
  dialog,
} = require("electron");

// AION O25N desktop backend local voice env lock
function aionO25NLocalVoiceBackendEnv() {
  return {
    ...process.env,
    PYTHONPATH: process.env.PYTHONPATH || process.cwd(),
    AION_VOICE_WORKER_ENABLED: "true",
    AION_TTS_PROVIDER: "kokoro",
    AION_LOCAL_VOICE_ENABLED: "true",
    AION_ELEVENLABS_ENABLED: "false",
    AION_BROWSER_SPEECH_FALLBACK_ENABLED: "false",
    AION_VOICE_NO_HIDDEN_DOWNLOADS: "true",
    AION_VOICE_RUNTIME_MODE: process.env.AION_VOICE_RUNTIME_MODE || "staging",
    // The desktop backend imports many historical semantic subsystems.  Keep
    // their shared MiniLM model off unified MPS memory and bound native thread
    // pools so opening the UI cannot starve the rest of macOS.
    AION_EMBEDDING_DEVICE: process.env.AION_EMBEDDING_DEVICE || "cpu",
    OMP_NUM_THREADS: process.env.OMP_NUM_THREADS || "2",
    MKL_NUM_THREADS: process.env.MKL_NUM_THREADS || "2",
    OPENBLAS_NUM_THREADS: process.env.OPENBLAS_NUM_THREADS || "2",
    VECLIB_MAXIMUM_THREADS: process.env.VECLIB_MAXIMUM_THREADS || "2",
    NUMEXPR_NUM_THREADS: process.env.NUMEXPR_NUM_THREADS || "2",
    TOKENIZERS_PARALLELISM: "false",
    AION_ENABLE_HQCE: "0",
    AION_ENABLE_GHX_TELEMETRY: "0",
    AION_ENABLE_DUAL_HEARTBEAT: "0",
    AION_ENABLE_BOOT_LOADER: "0",
    AION_SEED_PATTERNS: "0",
    GLYPHCHAIN_CONSENSUS_ENABLE: "0",
    HF_HUB_OFFLINE: "1",
    TRANSFORMERS_OFFLINE: "1",
    HF_DATASETS_OFFLINE: "1",
    TESSARIS_AION_FLOW_SESSION_KEY_PATH: process.env.TESSARIS_AION_FLOW_SESSION_KEY_PATH
      || path.join(os.homedir(), ".tessaris", "security", "aion-flow-desktop-session.key"),
  };
}
const path = require("path");
const fs = require("fs");
const os = require("os");
const crypto = require("crypto");
const { spawn } = require("child_process");
const http = require("http");
const { pathToFileURL } = require("url");

let mainWindow = null;
let isolatedBrowserWindow = null;
let isolatedBrowserProfileId = null;
let isolatedBrowserMissionKey = null;
let isolatedBrowserRecording = false;
let captureNextBrowserClick = false;
let captureNextClickArmed = false;
let spatialBoardroomBridge = null;
let spatialBoardroomProc = null;

let backendProc = null;
let backendSpawnedByApp = false;
let backendStartPromise = null;
let isQuitting = false;

const DEV_PROJECT_ROOT = "/Users/kevinrobinson/dev/COMDEX";
const BACKEND_HOST = "127.0.0.1";
const BACKEND_PORT = 8080;
const BACKEND_HEALTH_PATH = "/health";
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}${BACKEND_HEALTH_PATH}`;
// Historical full-stack fallback retained for explicit research sessions only.
const LEGACY_FULL_BACKEND_APP = "backend.main:app";
const DESKTOP_BACKEND_APP = process.env.TESSARIS_BACKEND_APP || "backend.desktop_app:app";
const AION_FLOW_SESSION_KEY_PATH = process.env.TESSARIS_AION_FLOW_SESSION_KEY_PATH
  || path.join(os.homedir(), ".tessaris", "security", "aion-flow-desktop-session.key");

const AION_CUSTOM_DEPARTMENT_WORKSPACE_ID = process.env.TESSARIS_FOUNDER_WORKSPACE_ID || "costa-conexion";
function normalizeAionCustomDepartmentWorkspaceId(value = "") {
  const workspaceId = String(value || AION_CUSTOM_DEPARTMENT_WORKSPACE_ID).trim().toLowerCase();
  return /^[a-z0-9][a-z0-9_.-]{0,119}$/.test(workspaceId)
    ? workspaceId
    : AION_CUSTOM_DEPARTMENT_WORKSPACE_ID;
}

function readAionCustomDepartments(workspaceId = AION_CUSTOM_DEPARTMENT_WORKSPACE_ID) {
  const safeWorkspaceId = normalizeAionCustomDepartmentWorkspaceId(workspaceId);
  const departmentFile = path.join(
    DEV_PROJECT_ROOT,
    ".runtime",
    "AION_BUSINESS",
    "business_containers",
    safeWorkspaceId,
    "department_intelligence.json",
  );
  try {
    const raw = JSON.parse(fs.readFileSync(departmentFile, "utf8"));
    const items = Array.isArray(raw?.custom_departments) ? raw.custom_departments : [];
    return items
      .filter((item) => item && item.core === false && typeof item.id === "string" && typeof item.name === "string")
      .map((item) => ({
        id: item.id,
        name: item.name,
        template: item.template,
        pilot_title: item.pilot_title,
        mandate: item.mandate,
        parent_department_id: item.parent_department_id || item.parent_id || null,
        core: false,
        created_at: item.created_at,
      }));
  } catch (error) {
    if (error?.code === "ENOENT") return [];
    throw error;
  }
}

const SPATIAL_BOARDROOM_APP_CANDIDATES = [
  process.env.TESSARIS_SPATIAL_BOARDROOM_APP,
  path.join(DEV_PROJECT_ROOT, "unity", "spatial-boardroom-mvp", "Builds", "macOS", "Tessaris Spatial Boardroom.app"),
  "/Volumes/Install macOS Sonoma/Tessaris/Unity/spatial-boardroom-mvp/Builds/macOS/Tessaris Spatial Boardroom.app",
].filter(Boolean);

function sanitizeSpatialBoardroomMember(raw = {}) {
  const id = String(raw.id || raw.key || raw.provider_id || "")
    .trim().toLowerCase().replace(/[^a-z0-9_.-]/g, "").slice(0, 64);
  if (!id) return null;
  return {
    id,
    label: String(raw.label || raw.name || id).trim().slice(0, 80),
    role: String(raw.role || (id === "aion" ? "Pilot" : "AI Board member")).trim().slice(0, 100),
    connected: raw.connected !== false,
  };
}

function resolveSpatialBoardroomExecutable() {
  for (const appPath of SPATIAL_BOARDROOM_APP_CANDIDATES) {
    const executable = path.join(appPath, "Contents", "MacOS", "Tessaris Spatial Boardroom");
    if (fs.existsSync(executable)) return { appPath, executable };
  }
  return null;
}

function enqueueSpatialBoardroomEvent(payload = {}) {
  if (!spatialBoardroomBridge) return null;
  const event = {
    id: `${Date.now()}-${crypto.randomBytes(5).toString("hex")}`,
    type: String(payload.type || "caption").slice(0, 64),
    role: String(payload.role || "").slice(0, 80),
    text: String(payload.text || "").slice(0, 1200),
    members: Array.isArray(payload.members)
      ? payload.members.map(sanitizeSpatialBoardroomMember).filter(Boolean).slice(0, 16)
      : [],
  };
  spatialBoardroomBridge.events.push(event);
  spatialBoardroomBridge.events = spatialBoardroomBridge.events.slice(-100);
  return event;
}

function readSmallJsonRequest(request, limit = 32768) {
  return new Promise((resolve, reject) => {
    let raw = "";
    request.setEncoding("utf8");
    request.on("data", (chunk) => {
      raw += chunk;
      if (raw.length > limit) {
        reject(new Error("payload_too_large"));
        request.destroy();
      }
    });
    request.on("end", () => {
      try { resolve(raw ? JSON.parse(raw) : {}); }
      catch { reject(new Error("invalid_json")); }
    });
    request.on("error", reject);
  });
}

async function ensureSpatialBoardroomBridge() {
  if (spatialBoardroomBridge?.server?.listening) return spatialBoardroomBridge;
  const token = crypto.randomBytes(32).toString("base64url");
  const bridge = { token, events: [], server: null, port: null };
  bridge.server = http.createServer(async (request, response) => {
    response.setHeader("Cache-Control", "no-store");
    response.setHeader("Content-Type", "application/json; charset=utf-8");
    const authorization = String(request.headers.authorization || "");
    const supplied = authorization.startsWith("Bearer ") ? authorization.slice(7) : "";
    const validToken = supplied.length === token.length
      && crypto.timingSafeEqual(Buffer.from(supplied), Buffer.from(token));
    if (!validToken) {
      response.writeHead(401); response.end(JSON.stringify({ error: "unauthorized" })); return;
    }
    const parsed = new URL(request.url || "/", "http://127.0.0.1");
    if (request.method === "GET" && parsed.pathname === "/events") {
      const after = parsed.searchParams.get("after") || "";
      let next = bridge.events[0];
      if (after) {
        const index = bridge.events.findIndex((item) => item.id === after);
        next = index >= 0 ? bridge.events[index + 1] : bridge.events[0];
      }
      if (!next) { response.writeHead(204); response.end(); return; }
      response.writeHead(200); response.end(JSON.stringify(next)); return;
    }
    if (request.method === "POST" && parsed.pathname === "/actions") {
      try {
        const payload = await readSmallJsonRequest(request);
        const type = String(payload.type || "").trim();
        const allowed = new Set(["open_board_member_chat", "open_executive_chat", "meeting_overview"]);
        if (!allowed.has(type)) throw new Error("unsupported_action");
        const clean = {
          type,
          member_id: String(payload.member_id || "").trim().toLowerCase().replace(/[^a-z0-9_.-]/g, "").slice(0, 64),
          label: String(payload.label || "").trim().slice(0, 80),
          role: String(payload.role || "").trim().slice(0, 100),
        };
        sendToMainWindow("aion-spatial-boardroom-action", clean);
        response.writeHead(202); response.end(JSON.stringify({ ok: true }));
      } catch (error) {
        response.writeHead(400); response.end(JSON.stringify({ error: error.message || "invalid_action" }));
      }
      return;
    }
    response.writeHead(404); response.end(JSON.stringify({ error: "not_found" }));
  });
  await new Promise((resolve, reject) => {
    bridge.server.once("error", reject);
    bridge.server.listen(0, "127.0.0.1", resolve);
  });
  bridge.port = bridge.server.address().port;
  spatialBoardroomBridge = bridge;
  return bridge;
}

function ensureAionFlowSessionKey() {
  fs.mkdirSync(path.dirname(AION_FLOW_SESSION_KEY_PATH), { recursive: true, mode: 0o700 });
  if (!fs.existsSync(AION_FLOW_SESSION_KEY_PATH)) {
    fs.writeFileSync(AION_FLOW_SESSION_KEY_PATH, crypto.randomBytes(32), { mode: 0o600, flag: "wx" });
  }
  fs.chmodSync(AION_FLOW_SESSION_KEY_PATH, 0o600);
  const value = fs.readFileSync(AION_FLOW_SESSION_KEY_PATH);
  if (value.length < 32) throw new Error("AION Flow desktop session key is invalid");
  return value;
}

function signAionFlowRequest(payload = {}) {
  const method = String(payload.method || "GET").toUpperCase();
  const target = String(payload.target || payload.path || "");
  const body = String(payload.body || "");
  const personId = String(payload.person_id || "").trim();
  const workspaceId = String(payload.workspace_id || "").trim();
  if (!target.startsWith("/api/workflow-capsules/aion-flow/")) throw new Error("AION Flow request target is outside the signed boundary");
  if (!personId || !workspaceId) throw new Error("Select an authenticated Boardroom person and workspace first");
  const key = ensureAionFlowSessionKey();
  const issuedAt = Math.floor(Date.now() / 1000);
  const nonce = crypto.randomBytes(16).toString("hex");
  const deviceId = `tessaris-desktop-${crypto.createHash("sha256").update(key).digest("hex").slice(0, 16)}`;
  const bodyHash = crypto.createHash("sha256").update(body).digest("hex");
  const message = ["aion.flow.desktop-session.v1", method, target, bodyHash, deviceId, personId, workspaceId, String(issuedAt), nonce].join("\n");
  const signature = crypto.createHmac("sha256", key).update(message).digest("hex");
  return {
    "x-aion-flow-device-id": deviceId,
    "x-aion-flow-person-id": personId,
    "x-aion-flow-workspace-id": workspaceId,
    "x-aion-flow-issued-at": String(issuedAt),
    "x-aion-flow-nonce": nonce,
    "x-aion-flow-body-sha256": bodyHash,
    "x-aion-flow-signature": signature,
  };
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function httpGet(url) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, (res) => {
      let data = "";

      res.on("data", (chunk) => {
        data += chunk;
      });

      res.on("end", () => {
        resolve({
          status: res.statusCode || 0,
          body: data,
        });
      });
    });

    req.on("error", reject);

    req.setTimeout(2000, () => {
      req.destroy(new Error("timeout"));
    });
  });
}

function httpPostJson(url, payload) {
  return new Promise((resolve, reject) => {
    const target = new URL(url);
    const body = JSON.stringify(payload || {});
    const req = http.request({
      hostname: target.hostname,
      port: target.port,
      path: `${target.pathname}${target.search}`,
      method: "POST",
      headers: {
        "content-type": "application/json",
        "content-length": Buffer.byteLength(body),
      },
    }, (res) => {
      const chunks = [];
      res.on("data", (chunk) => chunks.push(chunk));
      res.on("end", () => {
        const raw = Buffer.concat(chunks).toString("utf8");
        let parsed = {};
        try { parsed = JSON.parse(raw || "{}"); } catch {}
        if ((res.statusCode || 500) >= 400) {
          reject(new Error(parsed.error || `TTS HTTP ${res.statusCode}`));
          return;
        }
        resolve(parsed);
      });
    });
    req.on("error", reject);
    req.setTimeout(120000, () => req.destroy(new Error("TTS request timed out")));
    req.end(body);
  });
}

async function playAionLocalVoiceInMain(payload = {}) {
  const text = String(payload.text || "").trim();
  if (!text) return { ok: false, error: "Missing voice text" };

  const voicePayload = await httpPostJson(
    `http://${BACKEND_HOST}:${BACKEND_PORT}/api/aion/voice/tts-json`,
    {
      text,
      voice: String(payload.voice || "af_heart"),
      provider: "local",
    },
  );
  if (!voicePayload.ok || !voicePayload.audio_base64) {
    throw new Error(voicePayload.error || "TTS returned no audio");
  }

  const audioPath = path.join(
    os.tmpdir(),
    `aion_voice_${process.pid}_${Date.now()}.wav`,
  );
  fs.writeFileSync(audioPath, Buffer.from(voicePayload.audio_base64, "base64"));

  try {
    await new Promise((resolve, reject) => {
      const player = spawn("/usr/bin/afplay", [audioPath], {
        stdio: "ignore",
      });
      player.once("error", reject);
      player.once("exit", (code, signal) => {
        if (code === 0) resolve();
        else reject(new Error(`afplay stopped (${code ?? signal ?? "unknown"})`));
      });
    });
  } finally {
    try { fs.unlinkSync(audioPath); } catch {}
  }

  return {
    ok: true,
    provider: voicePayload.provider || "kokoro",
    elapsed_seconds: voicePayload.elapsed_seconds ?? null,
    persistent_worker: voicePayload.persistent_worker === true,
    worker_pid: voicePayload.worker_pid ?? null,
  };
}

let activeAionSystemVoiceProcess = null;

async function playAionSystemVoiceInMain(payload = {}) {
  const text = String(payload.text || "").trim().slice(0, 1200);
  if (!text) return { ok: false, error: "Missing voice text" };

  const allowedVoices = new Set(["Samantha", "Daniel", "Karen", "Moira", "Rishi", "Tessa"]);
  const requestedVoice = String(payload.voice || "Samantha").trim();
  const voice = allowedVoices.has(requestedVoice) ? requestedVoice : "Samantha";
  const rate = Math.max(130, Math.min(235, Number(payload.rate || 190)));

  try {
    if (activeAionSystemVoiceProcess && !activeAionSystemVoiceProcess.killed) {
      activeAionSystemVoiceProcess.kill("SIGTERM");
    }
  } catch {}

  return await new Promise((resolve) => {
    const speaker = spawn("/usr/bin/say", ["-v", voice, "-r", String(rate), text], {
      stdio: "ignore",
    });
    activeAionSystemVoiceProcess = speaker;
    speaker.once("error", (error) => {
      if (activeAionSystemVoiceProcess === speaker) activeAionSystemVoiceProcess = null;
      resolve({ ok: false, error: String(error?.message || error), provider: "macos_say" });
    });
    speaker.once("exit", (code, signal) => {
      if (activeAionSystemVoiceProcess === speaker) activeAionSystemVoiceProcess = null;
      resolve({
        ok: code === 0,
        provider: "macos_say",
        voice,
        interrupted: signal === "SIGTERM",
      });
    });
  });
}

async function isBackendHealthy() {
  try {
    const res = await httpGet(BACKEND_URL);
    return res.status >= 200 && res.status < 300;
  } catch (_) {
    return false;
  }
}

async function waitForBackendReady({ attempts = 30, delayMs = 1000 } = {}) {
  for (let i = 0; i < attempts; i += 1) {
    if (await isBackendHealthy()) {
      return true;
    }
    await wait(delayMs);
  }
  return false;
}

function findExistingPath(candidates) {
  for (const candidate of candidates) {
    if (candidate && fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return null;
}

function isPackagedApp() {
  return app.isPackaged;
}

function resolveProjectRoot() {
  const candidates = [];

  if (!isPackagedApp()) {
    candidates.push(
      process.env.TESSARIS_PROJECT_ROOT,
      DEV_PROJECT_ROOT,
      path.resolve(__dirname, "../../.."),
      process.cwd(),
    );
  } else {
    candidates.push(
      process.env.TESSARIS_PROJECT_ROOT,
      DEV_PROJECT_ROOT,
      process.cwd(),
    );
  }

  const root = candidates.find((candidate) => {
    return (
      candidate &&
      fs.existsSync(path.join(candidate, "backend")) &&
      fs.existsSync(path.join(candidate, ".venv"))
    );
  });

  if (!root) {
    throw new Error(
      [
        "Could not resolve COMDEX project root.",
        "Expected a folder containing both 'backend' and '.venv'.",
        "Packaged mode requires TESSARIS_PROJECT_ROOT or DEV_PROJECT_ROOT to exist locally.",
        "Checked:",
        ...candidates.filter(Boolean).map((item) => `- ${item}`),
      ].join("\n"),
    );
  }

  return root;
}

function resolvePythonBin(projectRoot) {
  const candidates = [
    path.join(projectRoot, ".venv", "bin", "python"),
    path.join(projectRoot, ".venv", "Scripts", "python.exe"),
  ];

  const pythonBin = findExistingPath(candidates);

  if (!pythonBin) {
    throw new Error(
      [
        "Could not find Python interpreter for local backend.",
        "Checked:",
        ...candidates.map((item) => `- ${item}`),
      ].join("\n"),
    );
  }

  return pythonBin;
}

function resolveIconPath() {
  const candidates = [
    path.join(__dirname, "..", "assets", "icon.png"),
    path.join(process.resourcesPath || "", "assets", "icon.png"),
  ];

  return (
    findExistingPath(candidates) ||
    path.join(__dirname, "..", "assets", "icon.png")
  );
}

function resolveRendererPath() {
  const candidates = [
    path.join(__dirname, "..", "src", "index.html"),
    path.join(process.resourcesPath || "", "src", "index.html"),
  ];

  const filePath = findExistingPath(candidates);

  if (!filePath) {
    throw new Error(
      [
        "Could not find desktop renderer entry file.",
        "Checked:",
        ...candidates.map((item) => `- ${item}`),
      ].join("\n"),
    );
  }

  return filePath;
}

function sendBackendStatus(payload) {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.webContents.send("backend-status", payload);
}

function sendToMainWindow(channel, payload) {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.webContents.send(channel, payload);
}

function installAionMicrophonePermissionPolicy() {
  const ses = session.defaultSession;
  if (!ses || ses.__aionMicrophonePermissionPolicyInstalled) return;
  ses.__aionMicrophonePermissionPolicyInstalled = true;

  ses.setPermissionCheckHandler((_webContents, permission, _origin, details = {}) => {
    if (permission !== "media") return false;
    const mediaType = String(details.mediaType || "").toLowerCase();
    return !mediaType || mediaType === "audio" || mediaType === "microphone";
  });

  ses.setPermissionRequestHandler((_webContents, permission, callback, details = {}) => {
    const mediaTypes = Array.isArray(details.mediaTypes)
      ? details.mediaTypes.map((item) => String(item).toLowerCase())
      : [];
    const allowAudio = permission === "media" &&
      (mediaTypes.length === 0 || mediaTypes.includes("audio"));
    callback(allowAudio);
  });
}

function cleanupBackendProcessState() {
  backendProc = null;
  backendSpawnedByApp = false;
}

function runtimeInfo() {
  let projectRoot = null;
  let pythonBin = null;
  let rendererPath = null;

  try {
    projectRoot = resolveProjectRoot();
  } catch (_) {
    projectRoot = null;
  }

  try {
    if (projectRoot) {
      pythonBin = resolvePythonBin(projectRoot);
    }
  } catch (_) {
    pythonBin = null;
  }

  try {
    rendererPath = resolveRendererPath();
  } catch (_) {
    rendererPath = null;
  }

  return {
    packaged: isPackagedApp(),
    resourcesPath: process.resourcesPath || null,
    cwd: process.cwd(),
    rendererPath,
    projectRoot,
    pythonBin,
    backendUrl: BACKEND_URL,
    backendManaged: backendSpawnedByApp,
    backendPid: backendProc?.pid ?? null,
    isolatedBrowserOpen:
      !!isolatedBrowserWindow && !isolatedBrowserWindow.isDestroyed(),
    isolatedBrowserRecording,
  };
}

function resolveIsolatedBrowserShellPath() {
  const candidates = [
    path.join(__dirname, "isolated-browser.html"),
    path.join(__dirname, "..", "electron", "isolated-browser.html"),
    path.join(process.resourcesPath || "", "electron", "isolated-browser.html"),
  ];

  const filePath = findExistingPath(candidates);

  if (!filePath) {
    throw new Error(
      [
        "Could not find isolated-browser.html.",
        "Checked:",
        ...candidates.map((item) => `- ${item}`),
      ].join("\n"),
    );
  }

  return filePath;
}

function getRecorderInjectionScript() {
  return `
    (() => {
      if (window.__AION_BROWSER_RECORDER_INSTALLED__) return;
      window.__AION_BROWSER_RECORDER_INSTALLED__ = true;
      window.__AION_BROWSER_RECORDING__ = false;
      window.__AION_CAPTURE_NEXT_CLICK__ = false;

      function nowIso() {
        return new Date().toISOString();
      }

      function safeString(value, max = 180) {
        const text = String(value || "").replace(/\\s+/g, " ").trim();
        return text.length > max ? text.slice(0, max) + "..." : text;
      }

      function cssEscape(value) {
        try {
          if (window.CSS && CSS.escape) return CSS.escape(value);
        } catch (_) {}
        return String(value || "").replace(/[^a-zA-Z0-9_-]/g, "\\\\$&");
      }

      function attrEscape(value) {
        return String(value || "").replace(/"/g, "\\\\\"");
      }

      function cssPath(el) {
        if (!el || !el.tagName) return "";
        if (el.id) return "#" + cssEscape(el.id);

        const parts = [];
        let node = el;

        while (node && node.nodeType === 1 && parts.length < 6) {
          let part = node.tagName.toLowerCase();

          const testId =
            node.getAttribute("data-testid") ||
            node.getAttribute("data-test") ||
            node.getAttribute("data-qa");

          if (testId) {
            part += '[data-testid="' + attrEscape(testId) + '"]';
            parts.unshift(part);
            break;
          }

          const aria = node.getAttribute("aria-label");
          if (aria) {
            part += '[aria-label="' + attrEscape(aria) + '"]';
            parts.unshift(part);
            break;
          }

          const role = node.getAttribute("role");
          if (role) {
            part += '[role="' + attrEscape(role) + '"]';
          }

          const name = node.getAttribute("name");
          if (name && ["input", "textarea", "select", "button"].includes(node.tagName.toLowerCase())) {
            part += '[name="' + attrEscape(name) + '"]';
            parts.unshift(part);
            break;
          }

          const parent = node.parentElement;
          if (parent) {
            const sameTag = Array.from(parent.children).filter(
              (x) => x.tagName === node.tagName,
            );
            if (sameTag.length > 1) {
              part += ":nth-of-type(" + (sameTag.indexOf(node) + 1) + ")";
            }
          }

          parts.unshift(part);
          node = parent;
        }

        return parts.join(" > ");
      }

      function stableSelector(el) {
        if (!el || !el.tagName) return "";

        const role = el.getAttribute("role");
        const aria = el.getAttribute("aria-label");
        const name = el.getAttribute("name");
        const id = el.getAttribute("id");
        const testId =
          el.getAttribute("data-testid") ||
          el.getAttribute("data-test") ||
          el.getAttribute("data-qa");

        if (id) return "#" + cssEscape(id);
        if (testId) return '[data-testid="' + attrEscape(testId) + '"]';
        if (aria) return el.tagName.toLowerCase() + '[aria-label="' + attrEscape(aria) + '"]';
        if (name) return el.tagName.toLowerCase() + '[name="' + attrEscape(name) + '"]';
        if (role) return el.tagName.toLowerCase() + '[role="' + attrEscape(role) + '"]';

        return cssPath(el);
      }

      function safeValue(el) {
        const type = String(el?.type || "").toLowerCase();
        const name = String(el?.name || "").toLowerCase();
        const id = String(el?.id || "").toLowerCase();
        const autocomplete = String(el?.autocomplete || "").toLowerCase();

        if (type === "password") return "[masked-password]";
        if (name.includes("password") || id.includes("password")) return "[masked-password]";
        if (autocomplete.includes("password")) return "[masked-password]";
        if (name.includes("token") || id.includes("token")) return "[masked-secret]";
        if (name.includes("secret") || id.includes("secret")) return "[masked-secret]";
        if (name.includes("card") || id.includes("card")) return "[masked-payment-field]";
        if (type === "file") return "[file-selected]";

        const value = String(el?.value || "");
        if (value.length > 120) return value.slice(0, 120) + "...";
        return value;
      }

      function labelFor(el) {
        if (!el) return "element";

        const labelledBy = el.getAttribute?.("aria-labelledby");
        if (labelledBy) {
          const node = document.getElementById(labelledBy.split(" ")[0]);
          const text = safeString(node?.innerText || node?.textContent || "");
          if (text) return text;
        }

        return (
          safeString(el.getAttribute?.("aria-label")) ||
          safeString(el.getAttribute?.("title")) ||
          safeString(el.innerText || el.textContent) ||
          safeString(el.placeholder) ||
          safeString(el.name) ||
          safeString(el.id) ||
          safeString(el.tagName?.toLowerCase?.()) ||
          "element"
        );
      }

      function nearestActionElement(target) {
        if (!target || !target.closest) return target;
        return (
          target.closest("button") ||
          target.closest("a") ||
          target.closest('[role="button"]') ||
          target.closest('[role="link"]') ||
          target.closest('[role="row"]') ||
          target.closest('[role="menuitem"]') ||
          target.closest("input") ||
          target.closest("textarea") ||
          target.closest("select") ||
          target
        );
      }

      function isRiskyLabel(text) {
        const lowered = String(text || "").toLowerCase();
        return (
          lowered.includes("send") ||
          lowered.includes("submit") ||
          lowered.includes("pay") ||
          lowered.includes("buy") ||
          lowered.includes("delete") ||
          lowered.includes("remove") ||
          lowered.includes("archive") ||
          lowered.includes("confirm") ||
          lowered.includes("publish") ||
          lowered.includes("post")
        );
      }

      function basePayload(event) {
        return {
          ...event,
          url: window.location.href,
          current_url: window.location.href,
          url_pattern: window.location.href,
          page_title: document.title || "",
          captured_at: nowIso(),
          source: "aion_isolated_browser_recorder",
        };
      }

      function emit(event, { force = false } = {}) {
        if (!force && !window.__AION_BROWSER_RECORDING__) return;

        const payload = basePayload(event);

        if (window.aionBrowserRecorder?.captureEvent) {
          window.aionBrowserRecorder.captureEvent(payload);
          return;
        }

        try {
          const { ipcRenderer } = require("electron");
          if (ipcRenderer?.sendToHost) {
            ipcRenderer.sendToHost("aion-browser-recorder-event", payload);
          }
        } catch (_) {}
      }

      function emitCapturedStep(event) {
        const payload = basePayload(event);

        if (window.aionBrowserRecorder?.capturedStep) {
          window.aionBrowserRecorder.capturedStep(payload);
        }

        if (window.aionBrowserRecorder?.captureEvent) {
          window.aionBrowserRecorder.captureEvent(payload);
        }
      }

      function highlight(el) {
        if (!el || !el.style) return;

        const previousOutline = el.style.outline;
        const previousBoxShadow = el.style.boxShadow;

        el.style.outline = "3px solid #1a8aff";
        el.style.boxShadow = "0 0 0 6px rgba(26, 138, 255, 0.18)";

        setTimeout(() => {
          try {
            el.style.outline = previousOutline;
            el.style.boxShadow = previousBoxShadow;
          } catch (_) {}
        }, 900);
      }

      window.__AION_BROWSER_RECORDER_START__ = () => {
        window.__AION_BROWSER_RECORDING__ = true;

        emit(
          {
            type: "open_page",
            event_type: "open_page",
            label: "Open " + (document.title || window.location.hostname || "page"),
            safety: "read_only",
            output: "page_context",
            selector: "",
            requires_approval: false,
          },
          { force: true },
        );
      };

      window.__AION_BROWSER_RECORDER_STOP__ = () => {
        window.__AION_BROWSER_RECORDING__ = false;
        window.__AION_CAPTURE_NEXT_CLICK__ = false;
      };

      window.__AION_CAPTURE_NEXT_CLICK_ARM__ = () => {
        window.__AION_CAPTURE_NEXT_CLICK__ = true;
        document.body?.setAttribute?.("data-aion-capture-next-click", "true");
      };

      window.__AION_CAPTURE_NEXT_CLICK_CANCEL__ = () => {
        window.__AION_CAPTURE_NEXT_CLICK__ = false;
        document.body?.removeAttribute?.("data-aion-capture-next-click");
      };

      document.addEventListener(
        "click",
        (e) => {
          const el = nearestActionElement(e.target);
          const text = labelFor(el);
          const selector = stableSelector(el);
          const risky = isRiskyLabel(text);

          if (window.__AION_CAPTURE_NEXT_CLICK__) {
            e.preventDefault();
            e.stopPropagation();

            window.__AION_CAPTURE_NEXT_CLICK__ = false;
            document.body?.removeAttribute?.("data-aion-capture-next-click");
            highlight(el);

            emitCapturedStep({
              type: "click_checkpoint",
              event_type: "click_checkpoint",
              label: "Click " + text,
              safety: risky ? "approval_required" : "interaction",
              output: "click_result",
              selector,
              element_text: text,
              tag_name: el?.tagName?.toLowerCase?.() || "",
              requires_approval: risky,
              notes: risky
                ? "Risky action detected. Requires approval before live execution."
                : "User selected this element as the intended workflow click.",
            });

            return false;
          }

          if (!window.__AION_BROWSER_RECORDING__) return;

          emit({
            type: risky ? "approval_checkpoint" : "click_element",
            event_type: risky ? "approval_checkpoint" : "click_element",
            label: risky
              ? "Approval required before clicking " + text
              : "Click " + text,
            safety: risky ? "approval_required" : "interaction",
            output: risky ? "approval_required" : "click_result",
            selector,
            element_text: text,
            tag_name: el?.tagName?.toLowerCase?.() || "",
            requires_approval: risky,
          });
        },
        true,
      );

      document.addEventListener(
        "input",
        (e) => {
          const el = e.target;
          if (!el || !("value" in el)) return;

          emit({
            type: "type_text",
            event_type: "type_text",
            label: "Type into " + labelFor(el),
            safety: "input",
            output: "field_value",
            selector: stableSelector(el),
            field_name: el.name || el.id || labelFor(el),
            value_hint: safeValue(el),
            requires_approval: false,
          });
        },
        true,
      );

      document.addEventListener(
        "change",
        (e) => {
          const el = e.target;
          if (!el) return;

          emit({
            type: el.tagName === "SELECT" ? "select_dropdown" : "change_field",
            event_type: el.tagName === "SELECT" ? "select_dropdown" : "change_field",
            label: "Change " + labelFor(el),
            safety: "input",
            output: "field_value",
            selector: stableSelector(el),
            field_name: el.name || el.id || labelFor(el),
            value_hint: safeValue(el),
            requires_approval: false,
          });
        },
        true,
      );
    })();
  `;
}

async function injectBrowserRecorder() {
  if (!isolatedBrowserWindow || isolatedBrowserWindow.isDestroyed()) {
    return { ok: false, error: "Isolated browser is not open" };
  }

  try {
    const recorderScript = JSON.stringify(getRecorderInjectionScript());
    const result = await isolatedBrowserWindow.webContents.executeJavaScript(
      `(async () => {
        if (!window.aionIsolatedBrowser?.installRecorder) {
          return { ok: false, error: "Isolated browser wrapper is not ready" };
        }
        return await window.aionIsolatedBrowser.installRecorder(${recorderScript});
      })()`,
      true,
    );
    return result?.ok ? result : { ok: false, error: result?.error || "Recorder install failed" };
  } catch (error) {
    return { ok: false, error: String(error?.message || error) };
  }
}

async function runInIsolatedBrowser(script) {
  if (!isolatedBrowserWindow || isolatedBrowserWindow.isDestroyed()) {
    return { ok: false, error: "Isolated browser is not open" };
  }

  try {
    const result = await isolatedBrowserWindow.webContents.executeJavaScript(
      script,
      true,
    );
    return { ok: true, result };
  } catch (error) {
    return { ok: false, error: String(error?.message || error) };
  }
}

async function loadUrlInIsolatedBrowser(startUrl) {
  if (!isolatedBrowserWindow || isolatedBrowserWindow.isDestroyed()) {
    return { ok: false, error: "Isolated browser is not open" };
  }

  if (!startUrl) return { ok: true, skipped: true };

  try {
    const result = await isolatedBrowserWindow.webContents.executeJavaScript(
      `
        (async () => {
          for (let i = 0; i < 50; i += 1) {
            if (
              window.aionIsolatedBrowser &&
              typeof window.aionIsolatedBrowser.loadUrl === "function"
            ) {
              window.aionIsolatedBrowser.loadUrl(${JSON.stringify(startUrl)});
              return {
                ok: true,
                loaded_via: "wrapper",
                hasWrapper: true,
                keys: Object.keys(window.aionIsolatedBrowser),
                title: document.title,
                url: window.location.href,
              };
            }

            await new Promise((resolve) => setTimeout(resolve, 100));
          }

          return {
            ok: false,
            error: "Aion isolated browser wrapper was not ready; refusing to replace wrapper with target URL.",
            hasWrapper: !!window.aionIsolatedBrowser,
            keys: window.aionIsolatedBrowser ? Object.keys(window.aionIsolatedBrowser) : [],
            title: document.title,
            url: window.location.href,
          };
        })()
      `,
      true,
    );

    console.log("[isolated-browser] loadUrl result", result);
    return result;
  } catch (error) {
    return { ok: false, error: String(error?.message || error) };
  }
}

async function openIsolatedBrowserWindow(
  startUrl = "https://mail.google.com/mail/u/0/#inbox",
  options = {},
) {
  const requestedProfile = String(options.browserProfileId || "aion-isolated-browser")
    .replace(/[^a-zA-Z0-9_.-]+/g, "-")
    .slice(0, 120) || "aion-isolated-browser";
  const departmentId = String(options.departmentId || "operations")
    .replace(/[^a-zA-Z0-9_.-]+/g, "-")
    .slice(0, 80) || "operations";
  const missionId = String(options.missionId || "").slice(0, 160);
  const taskId = String(options.taskId || "").slice(0, 160);
  const activityState = String(options.activityState || "idle").slice(0, 80);
  const objective = String(options.objective || "").replace(/\s+/g, " ").trim().slice(0, 1000);
  const missionKey = [missionId, taskId, activityState, objective].join("|");
  if (isolatedBrowserWindow && !isolatedBrowserWindow.isDestroyed()) {
    isolatedBrowserWindow.focus();

    let wrapperReady = false;
    try {
      wrapperReady = await isolatedBrowserWindow.webContents.executeJavaScript(
        `!!(window.aionIsolatedBrowser && typeof window.aionIsolatedBrowser.startRecorder === "function")`,
        true,
      );
    } catch (_) {
      wrapperReady = false;
    }

    const profileChanged = isolatedBrowserProfileId !== requestedProfile;
    const missionChanged = isolatedBrowserMissionKey !== missionKey;
    if (!wrapperReady || profileChanged || missionChanged) {
      console.log("[isolated-browser] loading isolated-browser.html shell", {
        wrapperReady,
        profileChanged,
        missionChanged,
        requestedProfile,
      });

      const shellPath = resolveIsolatedBrowserShellPath();
      const webviewPreloadPath = path.join(__dirname, "isolated-webview-preload.js");

      await isolatedBrowserWindow.loadFile(shellPath, {
        query: {
          webviewPreload: webviewPreloadPath,
          browserProfileId: requestedProfile,
          departmentId,
          missionId,
          taskId,
          activityState,
          objective,
        },
      });
      isolatedBrowserProfileId = requestedProfile;
      isolatedBrowserMissionKey = missionKey;

      await new Promise((resolve) => {
        isolatedBrowserWindow.webContents.once("did-finish-load", resolve);
      });
    }

    if (startUrl) {
      await loadUrlInIsolatedBrowser(startUrl);
    }

    return {
      ok: true,
      reused: true,
      wrapperReady,
      reloadedWrapper: !wrapperReady || profileChanged || missionChanged,
      profileChanged,
      browserProfileId: requestedProfile,
      departmentId,
      missionId,
      taskId,
      activityState,
      objective,
      url: startUrl,
    };
  }

  isolatedBrowserWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    title: "Aion Isolated Browser",
    icon: resolveIconPath(),
    backgroundColor: "#f3f6fb",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      webviewTag: true,
    },
  });

  isolatedBrowserWindow.on("closed", () => {
    isolatedBrowserWindow = null;
    isolatedBrowserProfileId = null;
    isolatedBrowserMissionKey = null;
    isolatedBrowserRecording = false;
    captureNextClickArmed = false;

    sendToMainWindow("browser-recorder-status", {
      ok: true,
      status: "closed",
      message: "Aion isolated browser closed",
      created_at: new Date().toISOString(),
    });
  });

  isolatedBrowserWindow.webContents.on("did-finish-load", async () => {
    await injectBrowserRecorder();

    sendToMainWindow("browser-recorder-status", {
      ok: true,
      status: "loaded",
      message: "Aion isolated browser loaded",
      url: isolatedBrowserWindow?.webContents.getURL() || "",
      title: isolatedBrowserWindow?.webContents.getTitle() || "",
      created_at: new Date().toISOString(),
    });

    if (isolatedBrowserRecording) {
      const recorderScript = JSON.stringify(getRecorderInjectionScript());
      await runInIsolatedBrowser(
        `window.aionIsolatedBrowser?.startRecorder(${recorderScript})`,
      );
    }

    if (captureNextClickArmed) {
      await runInIsolatedBrowser(
        "window.__AION_CAPTURE_NEXT_CLICK_ARM__ && window.__AION_CAPTURE_NEXT_CLICK_ARM__()",
      );
    }
  });

  const shellPath = resolveIsolatedBrowserShellPath();
  const webviewPreloadPath = path.join(__dirname, "isolated-webview-preload.js");

  await isolatedBrowserWindow.loadFile(shellPath, {
    query: {
      webviewPreload: webviewPreloadPath,
      browserProfileId: requestedProfile,
      departmentId,
      missionId,
      taskId,
      activityState,
      objective,
    },
  });
  isolatedBrowserProfileId = requestedProfile;
  isolatedBrowserMissionKey = missionKey;

  // loadFile resolves after the wrapper has finished loading. Registering a
  // one-shot did-finish-load listener here is therefore too late and leaves
  // a newly created window on its historical Gmail default. Navigate the
  // wrapper's webview explicitly before reporting success.
  const navigation = await loadUrlInIsolatedBrowser(startUrl);
  if (!navigation?.ok) {
    return {
      ok: false,
      reused: false,
      url: startUrl,
      error: navigation?.error || "The isolated browser could not load the requested URL.",
    };
  }

  return {
    ok: true,
    reused: false,
    url: startUrl,
    browserProfileId: requestedProfile,
    departmentId,
    missionId,
    taskId,
    activityState,
    objective,
    navigation,
  };
}

async function ensureBackendRunning() {
  if (backendStartPromise) {
    return backendStartPromise;
  }

  backendStartPromise = (async () => {
    if (await isBackendHealthy()) {
      console.log(`[backend] already healthy on ${BACKEND_HOST}:${BACKEND_PORT}`);
      return { ok: true, mode: "existing" };
    }

    if (backendProc) {
      const ready = await waitForBackendReady();
      return ready
        ? { ok: true, mode: backendSpawnedByApp ? "spawned" : "existing" }
        : { ok: false, mode: backendSpawnedByApp ? "spawned" : "existing" };
    }

    const projectRoot = resolveProjectRoot();
    const pythonBin = resolvePythonBin(projectRoot);

    // The O25N launcher contract calls the governed environment builder with
    // no ad-hoc overrides.  Seed its process-local inputs first so the child
    // still receives the canonical repository root.
    process.env.PYTHONUNBUFFERED = "1";
    process.env.TESSARIS_PROJECT_ROOT = projectRoot;
    process.env.PYTHONPATH = projectRoot;

    console.log(`[backend] project root: ${projectRoot}`);
    console.log(`[backend] python bin: ${pythonBin}`);

    const proc = spawn(pythonBin, [
      "-m",
      "uvicorn",
      DESKTOP_BACKEND_APP,
      "--host",
      "127.0.0.1",
      "--port",
      "8080",
    ], {
      cwd: projectRoot,
      env: aionO25NLocalVoiceBackendEnv(),
      stdio: "pipe",
    });

    backendProc = proc;
    backendSpawnedByApp = true;

    proc.stdout.on("data", (data) => {
      process.stdout.write(`[backend] ${data}`);
    });

    proc.stderr.on("data", (data) => {
      process.stderr.write(`[backend] ${data}`);
    });

    proc.on("error", (error) => {
      console.error(`[backend] spawn error: ${error.message}`);
      sendBackendStatus({
        ok: false,
        status: "spawn_error",
        detail: error.message,
      });
      cleanupBackendProcessState();
    });

    proc.on("exit", (code, signal) => {
      console.log(`[backend] exited code=${code} signal=${signal}`);

      const wasManaged = backendSpawnedByApp;
      cleanupBackendProcessState();

      if (!isQuitting && wasManaged) {
        sendBackendStatus({
          ok: false,
          status: "stopped",
          detail: `Backend exited (${signal || code || "unknown"})`,
        });
      }
    });

    const ready = await waitForBackendReady({ attempts: 45, delayMs: 1000 });

    if (!ready) {
      return { ok: false, mode: "spawned" };
    }

    return { ok: true, mode: "spawned" };
  })();

  try {
    return await backendStartPromise;
  } finally {
    backendStartPromise = null;
  }
}

async function stopBackend() {
  if (!backendProc || !backendSpawnedByApp) {
    return;
  }

  const proc = backendProc;

  try {
    proc.kill("SIGTERM");
  } catch (_) {
    cleanupBackendProcessState();
    return;
  }

  for (let i = 0; i < 20; i += 1) {
    if (!backendProc) {
      return;
    }
    await wait(100);
  }

  try {
    proc.kill("SIGKILL");
  } catch (_) {
    // ignore
  }
}


async function armBrowserCaptureNextClick() {
  if (!isolatedBrowserWindow || isolatedBrowserWindow.isDestroyed()) {
    return {
      ok: false,
      status: "no_isolated_browser",
      message: "Open the isolated browser before capturing a click.",
      created_at: new Date().toISOString(),
    };
  }

  try {
    const js = `
      (async () => {
        for (let i = 0; i < 50; i += 1) {
          if (
            window.aionIsolatedBrowser &&
            typeof window.aionIsolatedBrowser.captureNextClickOnce === "function"
          ) {
            return await window.aionIsolatedBrowser.captureNextClickOnce();
          }

          await new Promise((resolve) => setTimeout(resolve, 100));
        }

        return {
          ok: false,
          error: "window.aionIsolatedBrowser.captureNextClickOnce not available",
          hasWrapper: !!window.aionIsolatedBrowser,
          keys: window.aionIsolatedBrowser ? Object.keys(window.aionIsolatedBrowser) : [],
          title: document.title,
          url: window.location.href,
        };
      })()
    `;

    const result = await isolatedBrowserWindow.webContents.executeJavaScript(js, true);
    const payload = result?.payload || null;

    console.log("[browser-recorder] direct click capture result", result);

    if (payload) {
      sendToMainWindow("browser-recorder-event", payload);
      sendToMainWindow("browser-operator-captured-step", payload);
    }

    return {
      ok: result?.ok === true,
      status: result?.ok === true ? "captured_click" : "capture_next_click_failed",
      message: result?.ok === true
        ? "Browser click captured."
        : result?.error || "Browser click capture failed.",
      result,
      payload,
      created_at: new Date().toISOString(),
    };
  } catch (error) {
    return {
      ok: false,
      status: "capture_next_click_failed",
      message: String(error?.message || error),
      created_at: new Date().toISOString(),
    };
  }
}

ipcMain.handle("aion-start-capture-next-click", async () => {
  return await armBrowserCaptureNextClick();
});

ipcMain.handle("browser-operator-capture-next-click", async () => {
  return await armBrowserCaptureNextClick();
});

ipcMain.handle("aion-open-isolated-browser", async (_event, payload = {}) => {
  const startUrl =
    payload.startUrl ||
    payload.url ||
    "https://mail.google.com/mail/u/0/#inbox";

  return await openIsolatedBrowserWindow(startUrl, {
    browserProfileId: payload.browser_profile_id || payload.browserProfileId,
    departmentId: payload.department_id || payload.departmentId,
    missionId: payload.mission_id || payload.missionId,
    taskId: payload.task_id || payload.taskId,
    activityState: payload.activity_state || payload.activityState,
    objective: payload.objective,
  });
});

ipcMain.handle("browser-operator-open-isolated-browser", async (_event, payload = {}) => {
  const startUrl =
    payload.startUrl ||
    payload.url ||
    "https://mail.google.com/mail/u/0/#inbox";

  return await openIsolatedBrowserWindow(startUrl, {
    browserProfileId: payload.browser_profile_id || payload.browserProfileId,
    departmentId: payload.department_id || payload.departmentId,
    missionId: payload.mission_id || payload.missionId,
    taskId: payload.task_id || payload.taskId,
    activityState: payload.activity_state || payload.activityState,
    objective: payload.objective,
  });
});

ipcMain.handle("aion-start-browser-recording", async () => {
  isolatedBrowserRecording = true;
  let injected = { ok: true };

  if (isolatedBrowserWindow && !isolatedBrowserWindow.isDestroyed()) {
    const recorderScript = JSON.stringify(getRecorderInjectionScript());
    injected = await runInIsolatedBrowser(
      `window.aionIsolatedBrowser?.startRecorder(${recorderScript})`,
    );
  }

  return {
    ok: injected.ok,
    status: "recording",
    message: injected.ok ? "Browser recorder started" : injected.error,
    created_at: new Date().toISOString(),
  };
});


ipcMain.handle("aion-stop-browser-recording", async () => {
  isolatedBrowserRecording = false;
  captureNextClickArmed = false;

  if (isolatedBrowserWindow && !isolatedBrowserWindow.isDestroyed()) {
    await runInIsolatedBrowser(
      "window.aionIsolatedBrowser?.stopRecorder()",
    );
  }

  return {
    ok: true,
    status: "stopped",
    message: "Browser recorder stopped",
    created_at: new Date().toISOString(),
  };
});

ipcMain.handle("aion-replay-browser-skill", async (_event, payload = {}) => {
  if (!isolatedBrowserWindow || isolatedBrowserWindow.isDestroyed()) {
    return { ok: false, status: "no_isolated_browser", error: "Open the isolated browser before validating a skill." };
  }
  // Semantic replay is intentionally validation-only here. Live browser work must
  // arrive through the External Tool Gateway after its exact payload approval has
  // been verified server-side; renderer-supplied hashes are never authority.
  if (payload.mode === "live") {
    return {
      ok: false,
      status: "live_execution_requires_backend_gateway",
      error: "Live skill execution must use AION's governed tool queue and exact-payload approval.",
    };
  }
  const safePayload = {
    steps: Array.isArray(payload.steps) ? payload.steps.slice(0, 200) : [],
    inputs: payload.inputs && typeof payload.inputs === "object" ? payload.inputs : {},
    mode: "dry_run",
  };
  const serialized = JSON.stringify(safePayload);
  try {
    return await isolatedBrowserWindow.webContents.executeJavaScript(`
      (async () => {
        for (let attempt = 0; attempt < 50; attempt += 1) {
          if (window.aionIsolatedBrowser?.replaySemanticSteps) {
            return await window.aionIsolatedBrowser.replaySemanticSteps(${serialized});
          }
          await new Promise((resolve) => setTimeout(resolve, 100));
        }
        return { ok: false, status: "replay_bridge_unavailable" };
      })()
    `, true);
  } catch (error) {
    return { ok: false, status: "replay_failed", error: String(error?.message || error) };
  }
});


ipcMain.on("aion-browser-recorder-event", (_event, payload = {}) => {
  console.log("[browser-recorder-event]", payload?.type, payload?.label, payload?.selector || "");

  sendToMainWindow("browser-recorder-event", payload);

  if (captureNextBrowserClick && String(payload?.type || "").includes("click")) {
    captureNextBrowserClick = false;
  }
});

ipcMain.on("browser-operator-captured-step-from-page", (_event, payload = {}) => {
  captureNextClickArmed = false;

  const normalized = {
    ...payload,
    type: payload.type || payload.event_type || "click_checkpoint",
    event_type: payload.event_type || payload.type || "click_checkpoint",
    captured_at: payload.captured_at || new Date().toISOString(),
  };

  sendToMainWindow("browser-operator-captured-step", normalized);
  sendToMainWindow("browser-recorder-event", normalized);
});

ipcMain.on("aion-isolated-browser-loaded", (_event, payload = {}) => {
  sendToMainWindow("browser-recorder-status", {
    ok: true,
    status: "loaded",
    ...payload,
    created_at: new Date().toISOString(),
  });
});

function createWindow() {
  const iconPath = resolveIconPath();

  mainWindow = new BrowserWindow({
    width: 1600,
    height: 980,
    minWidth: 1280,
    minHeight: 800,
    title: "Tessaris",
    icon: iconPath,
    backgroundColor: "#f3f6fb",
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  const rendererPath = resolveRendererPath();
  mainWindow.loadFile(rendererPath);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

async function bootBackendForWindow() {
  sendBackendStatus({
    ok: false,
    status: "starting",
    detail: "Checking local backend...",
  });

  try {
    const result = await ensureBackendRunning();

    if (result.ok) {
      sendBackendStatus({
        ok: true,
        status: "ready",
        detail:
          result.mode === "existing"
            ? "Connected to existing local backend."
            : "Started local backend.",
      });
      return;
    }

    sendBackendStatus({
      ok: false,
      status: "timeout",
      detail: "Local backend did not become ready in time.",
    });
  } catch (error) {
    sendBackendStatus({
      ok: false,
      status: "startup_error",
      detail: error instanceof Error ? error.message : String(error),
    });
  }
}

app.name = "Tessaris";

ipcMain.handle("desktop-backend-restart", async () => {
  await stopBackend();
  cleanupBackendProcessState();
  return await ensureBackendRunning();
});

ipcMain.handle("desktop-backend-status", async () => {
  const healthy = await isBackendHealthy();
  return {
    healthy,
    managed: backendSpawnedByApp,
    pid: backendProc?.pid ?? null,
    url: BACKEND_URL,
  };
});

ipcMain.handle("desktop-runtime-info", async () => {
  return runtimeInfo();
});

ipcMain.handle("aion-flow-sign-request", async (_event, payload = {}) => {
  return signAionFlowRequest(payload);
});

ipcMain.handle("aion-custom-departments-list", async (_event, payload = {}) => {
  const workspaceId = normalizeAionCustomDepartmentWorkspaceId(payload.workspace_id);
  return {
    workspace_id: workspaceId,
    departments: readAionCustomDepartments(workspaceId),
  };
});

ipcMain.handle("aion-launch-spatial-boardroom", async (_event, payload = {}) => {
  const resolved = resolveSpatialBoardroomExecutable();
  if (!resolved) {
    return {
      ok: false,
      error: "native_build_not_found",
      message: "The native Spatial Boardroom build is not installed yet.",
      searched: SPATIAL_BOARDROOM_APP_CANDIDATES,
    };
  }
  const bridge = await ensureSpatialBoardroomBridge();
  const members = Array.isArray(payload.members)
    ? payload.members.map(sanitizeSpatialBoardroomMember).filter((member) => member?.connected).slice(0, 16)
    : [];
  if (!members.some((member) => member.id === "aion")) {
    members.unshift({ id: "aion", label: "AION", role: "Pilot", connected: true });
  }
  enqueueSpatialBoardroomEvent({ type: "board_members_snapshot", members });
  enqueueSpatialBoardroomEvent({
    type: "caption",
    text: `Connected Board intelligence: ${members.map((member) => member.label).join(", ")}. Select a member to open their Tessaris chat.`,
  });
  if (spatialBoardroomProc && !spatialBoardroomProc.killed) {
    enqueueSpatialBoardroomEvent({ type: "meeting_overview" });
    return { ok: true, mode: "native", status: "already_running", app_path: resolved.appPath };
  }
  spatialBoardroomProc = spawn(resolved.executable, [
    `--tessaris-endpoint=http://127.0.0.1:${bridge.port}/events`,
    `--tessaris-actions=http://127.0.0.1:${bridge.port}/actions`,
    `--tessaris-session=${bridge.token}`,
  ], { stdio: "ignore" });
  spatialBoardroomProc.once("exit", () => { spatialBoardroomProc = null; });
  spatialBoardroomProc.once("error", () => { spatialBoardroomProc = null; });
  return { ok: true, mode: "native", status: "launched", app_path: resolved.appPath };
});

ipcMain.handle("aion-spatial-boardroom-event", async (_event, payload = {}) => {
  if (!spatialBoardroomBridge) return { ok: false, error: "spatial_boardroom_not_running" };
  const event = enqueueSpatialBoardroomEvent(payload);
  return { ok: Boolean(event), event_id: event?.id || null };
});

ipcMain.handle("aion-open-external-url", async (_event, rawUrl = "") => {
  const value = String(rawUrl || "").trim();
  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    return { ok: false, error: "invalid_url" };
  }
  if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
    return { ok: false, error: "unsupported_protocol" };
  }
  await shell.openExternal(parsed.toString());
  return { ok: true };
});

ipcMain.handle("aion-open-business-artifact", async (_event, rawStoragePath = "") => {
  const value = String(rawStoragePath || "").trim();
  if (!value) return { ok: false, error: "artifact_path_missing" };
  const runtimeRoot = path.resolve(DEV_PROJECT_ROOT, ".runtime", "AION_BUSINESS");
  let candidate;
  if (path.isAbsolute(value)) {
    candidate = path.resolve(value);
  } else if (value.startsWith(".runtime/AION_BUSINESS/")) {
    candidate = path.resolve(DEV_PROJECT_ROOT, value);
  } else {
    candidate = path.resolve(runtimeRoot, value);
  }
  if (candidate !== runtimeRoot && !candidate.startsWith(`${runtimeRoot}${path.sep}`)) {
    return { ok: false, error: "artifact_path_outside_business_runtime" };
  }
  if (!fs.existsSync(candidate) || !fs.statSync(candidate).isFile()) {
    return { ok: false, error: "artifact_file_missing" };
  }
  const error = await shell.openPath(candidate);
  return error ? { ok: false, error } : { ok: true };
});

ipcMain.handle("aion-choose-local-video", async () => {
  const owner = BrowserWindow.getFocusedWindow() || mainWindow || undefined;
  const result = await dialog.showOpenDialog(owner, {
    title: "Choose source video",
    properties: ["openFile"],
    filters: [{ name: "Video", extensions: ["mp4", "mov", "m4v", "webm"] }],
  });
  if (result.canceled || !result.filePaths?.[0]) return { ok: false, canceled: true };
  return { ok: true, path: result.filePaths[0] };
});

ipcMain.handle("aion-choose-local-media", async (_event, payload = {}) => {
  const owner = BrowserWindow.getFocusedWindow() || mainWindow || undefined;
  const kind = String(payload.kind || "video").toLowerCase();
  const filters = {
    video: [{ name: "Video", extensions: ["mp4", "mov", "m4v", "webm"] }],
    image: [{ name: "Image", extensions: ["png", "jpg", "jpeg", "webp"] }],
    audio: [{ name: "Audio", extensions: ["mp3", "wav", "m4a", "aac", "flac"] }],
    document: [{ name: "People document", extensions: ["pdf", "docx", "txt", "md", "csv", "json"] }],
  };
  const result = await dialog.showOpenDialog(owner, {
    title: String(payload.title || `Choose ${kind}`),
    properties: payload.multiple === true ? ["openFile", "multiSelections"] : ["openFile"],
    filters: filters[kind] || filters.video,
  });
  if (result.canceled || !result.filePaths?.length) return { ok: false, canceled: true, paths: [] };
  return { ok: true, paths: result.filePaths, path: result.filePaths[0] };
});

ipcMain.handle("aion-play-local-voice", async (_event, payload = {}) => {
  try {
    return await playAionLocalVoiceInMain(payload);
  } catch (error) {
    return { ok: false, error: String(error?.message || error) };
  }
});

ipcMain.handle("aion-play-system-voice", async (_event, payload = {}) => {
  return await playAionSystemVoiceInMain(payload);
});

ipcMain.handle("aion-request-microphone-permission", async () => {
  if (process.platform !== "darwin") return { granted: true, status: "not_required" };
  const before = systemPreferences.getMediaAccessStatus("microphone");
  if (before === "granted") return { granted: true, status: before };
  if (before === "denied" || before === "restricted") {
    return { granted: false, status: before };
  }
  const granted = await systemPreferences.askForMediaAccess("microphone");
  return {
    granted: granted === true,
    status: systemPreferences.getMediaAccessStatus("microphone"),
  };
});

app.on("before-quit", async (event) => {
  if (isQuitting) {
    return;
  }

  isQuitting = true;
  event.preventDefault();

  if (spatialBoardroomBridge?.server) {
    try { spatialBoardroomBridge.server.close(); } catch {}
    spatialBoardroomBridge = null;
  }

  try {
    await stopBackend();
  } finally {
    app.exit(0);
  }
});

app.whenReady().then(async () => {
  installAionMicrophonePermissionPolicy();
  // AION O25P: start backend before loading renderer.
  // The renderer contains many eager backend fetchers; loading it before
  // backend readiness causes request storms and white-screen/freeze behaviour.
  let backendBootResult = { ok: false, mode: "not_started" };
  try {
    backendBootResult = await ensureBackendRunning();
  } catch (error) {
    console.error("[backend] pre-render startup failed:", error);
    backendBootResult = {
      ok: false,
      mode: "startup_error",
      detail: error instanceof Error ? error.message : String(error),
    };
  }

  createWindow();

  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.once("did-finish-load", () => {
      sendBackendStatus({
        ok: !!backendBootResult.ok,
        status: backendBootResult.ok ? "ready" : "startup_error",
        detail: backendBootResult.ok
          ? (backendBootResult.mode === "existing"
              ? "Connected to existing local backend."
              : "Started local backend.")
          : (backendBootResult.detail || "Local backend did not become ready before renderer load."),
      });
    });
  }

  app.on("activate", async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      try {
        await ensureBackendRunning();
      } catch (error) {
        console.error("[backend] activate startup failed:", error);
      }
      createWindow();

      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.once("did-finish-load", () => {
          void bootBackendForWindow();
        });
      }
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});


/* BEGIN AION D1 DEVTOOLS SHORTCUT REPAIR */
function installAionD1DevToolsShortcutRepair() {
  function toggleFocusedDevTools() {
    const focused = BrowserWindow.getFocusedWindow();
    const win = focused || BrowserWindow.getAllWindows()[0];

    if (!win || win.isDestroyed()) {
      return false;
    }

    if (win.webContents.isDevToolsOpened()) {
      win.webContents.closeDevTools();
    } else {
      win.webContents.openDevTools({ mode: "detach" });
    }

    return true;
  }

  app.whenReady().then(() => {
    try {
      globalShortcut.unregister("CommandOrControl+Alt+I");
      globalShortcut.unregister("F12");
    } catch {}

    try {
      globalShortcut.register("CommandOrControl+Alt+I", toggleFocusedDevTools);
      globalShortcut.register("F12", toggleFocusedDevTools);
    } catch (error) {
      console.warn("[AION] D1 DevTools globalShortcut failed", error);
    }

    try {
      const menu = Menu.buildFromTemplate([
        {
          label: "Tessaris",
          submenu: [
            { role: "about" },
            { type: "separator" },
            {
              label: "Toggle DevTools",
              accelerator: "CommandOrControl+Alt+I",
              click: toggleFocusedDevTools,
            },
            {
              label: "Open DevTools Detached",
              accelerator: "F12",
              click: toggleFocusedDevTools,
            },
            { type: "separator" },
            { role: "quit" },
          ],
        },
        {
          label: "Edit",
          submenu: [
            { role: "undo" },
            { role: "redo" },
            { type: "separator" },
            { role: "cut" },
            { role: "copy" },
            { role: "paste" },
            { role: "selectAll" },
          ],
        },
        {
          label: "View",
          submenu: [
            { role: "reload" },
            { role: "forceReload" },
            {
              label: "Toggle DevTools",
              accelerator: "CommandOrControl+Alt+I",
              click: toggleFocusedDevTools,
            },
            { type: "separator" },
            { role: "resetZoom" },
            { role: "zoomIn" },
            { role: "zoomOut" },
            { type: "separator" },
            { role: "togglefullscreen" },
          ],
        },
      ]);

      Menu.setApplicationMenu(menu);
    } catch (error) {
      console.warn("[AION] D1 DevTools menu install failed", error);
    }

    console.info("[AION] D1 DevTools shortcut repair installed");
  });
}

installAionD1DevToolsShortcutRepair();
/* END AION D1 DEVTOOLS SHORTCUT REPAIR */
