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
  screen,
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
    TESSARIS_APPLICATION_ACCOUNT_RECOVERY_DIR: process.env.TESSARIS_APPLICATION_ACCOUNT_RECOVERY_DIR
      || path.join(os.homedir(), ".tessaris", "security", "application-account-recovery"),
  };
}
const path = require("path");
const fs = require("fs");
const os = require("os");
const crypto = require("crypto");
const { spawn } = require("child_process");
const http = require("http");
const net = require("net");
const { pathToFileURL } = require("url");

let mainWindow = null;
let sentinelWindow = null;
let isolatedBrowserWindow = null;
let isolatedBrowserProfileId = null;
let isolatedBrowserMissionKey = null;
let isolatedBrowserRecording = false;
let captureNextBrowserClick = false;
let captureNextClickArmed = false;
let spatialBoardroomBridge = null;
let spatialBoardroomProc = null;
let pilotDashboardWindow = null;
let pilotServiceProc = null;
let pilotServiceStartPromise = null;
let pilotServiceLastError = "";

let backendProc = null;
let backendSpawnedByApp = false;
let backendStartPromise = null;
let backendRestartTimer = null;
let isQuitting = false;
let mainWindowState = { maximized: true, normalBounds: null };
let mainWindowStateWriteTimer = null;

// macOS may register both /Applications/Tessaris.app and a packaged
// development copy as distinct launchable applications. Electron's standard
// lock is bundle-scoped in that case, so both copies can otherwise appear in
// the Dock at once. This shared PID lock is deliberately outside either bundle.
const TESSARIS_DESKTOP_INSTANCE_PATH = path.join(
  os.homedir(),
  "Library",
  "Application Support",
  "Tessaris",
  "desktop-instance.pid",
);

function isTessarisProcessAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

function acquireTessarisDesktopProcessLock() {
  fs.mkdirSync(path.dirname(TESSARIS_DESKTOP_INSTANCE_PATH), { recursive: true });

  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const descriptor = fs.openSync(TESSARIS_DESKTOP_INSTANCE_PATH, "wx", 0o600);
      fs.writeFileSync(descriptor, String(process.pid), "utf8");
      fs.closeSync(descriptor);
      return true;
    } catch (error) {
      if (error?.code !== "EEXIST") throw error;

      let ownerPid = 0;
      try {
        ownerPid = Number.parseInt(fs.readFileSync(TESSARIS_DESKTOP_INSTANCE_PATH, "utf8").trim(), 10);
      } catch {}

      if (ownerPid !== process.pid && isTessarisProcessAlive(ownerPid)) {
        return false;
      }

      try { fs.unlinkSync(TESSARIS_DESKTOP_INSTANCE_PATH); } catch {}
    }
  }

  return false;
}

function releaseTessarisDesktopProcessLock() {
  try {
    const ownerPid = Number.parseInt(fs.readFileSync(TESSARIS_DESKTOP_INSTANCE_PATH, "utf8").trim(), 10);
    if (ownerPid === process.pid) fs.unlinkSync(TESSARIS_DESKTOP_INSTANCE_PATH);
  } catch {}
}

const tessarisHasDesktopProcessLock = acquireTessarisDesktopProcessLock();
if (!tessarisHasDesktopProcessLock) {
  process.exit(0);
}

process.on("exit", releaseTessarisDesktopProcessLock);

const tessarisHasSingleInstanceLock = app.requestSingleInstanceLock();
if (!tessarisHasSingleInstanceLock) {
  releaseTessarisDesktopProcessLock();
  process.exit(0);
}

app.on("second-instance", () => {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
});

const DEV_PROJECT_ROOT = "/Users/kevinrobinson/dev/COMDEX";
const BACKEND_HOST = "127.0.0.1";
const BACKEND_PORT = 8080;
const BACKEND_HEALTH_PATH = "/health";
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}${BACKEND_HEALTH_PATH}`;
const PILOT_HOST = "127.0.0.1";
const PILOT_PORT = 8765;
const PILOT_DASHBOARD_URL = `http://${PILOT_HOST}:${PILOT_PORT}/`;
const PILOT_RUNTIME_DIR = path.join(
  os.homedir(),
  "Library",
  "Application Support",
  "Pilot Fabric",
  ".runtime",
  "aion_fabric",
);
const PILOT_LOG_PATH = path.join(PILOT_RUNTIME_DIR, "tessaris-pilot-service.log");
// Historical full-stack fallback retained for explicit research sessions only.
const LEGACY_FULL_BACKEND_APP = "backend.main:app";
const DESKTOP_BACKEND_APP = process.env.TESSARIS_BACKEND_APP || "backend.desktop_app:app";
const AION_FLOW_SESSION_KEY_PATH = process.env.TESSARIS_AION_FLOW_SESSION_KEY_PATH
  || path.join(os.homedir(), ".tessaris", "security", "aion-flow-desktop-session.key");
const APPLICATION_ACCOUNT_DESCRIPTOR_PATH = path.join(
  process.env.TESSARIS_APPLICATION_ACCOUNT_RECOVERY_DIR
    || path.join(os.homedir(), ".tessaris", "security", "application-account-recovery"),
  "account-descriptor.json",
);

function pilotRequestJson(requestPath, { method = "GET", body = null, timeoutMs = 1800 } = {}) {
  return new Promise((resolve, reject) => {
    const encodedBody = body == null ? null : Buffer.from(JSON.stringify(body), "utf8");
    const request = http.request({
      host: PILOT_HOST,
      port: PILOT_PORT,
      path: requestPath,
      method,
      timeout: timeoutMs,
      headers: {
        Accept: "application/json",
        ...(method === "POST" ? { "X-AION-Fabric": "dashboard-v1" } : {}),
        ...(encodedBody ? {
          "Content-Type": "application/json; charset=utf-8",
          "Content-Length": encodedBody.length,
        } : {}),
      },
    }, (response) => {
      const chunks = [];
      let receivedBytes = 0;
      response.on("data", (chunk) => {
        receivedBytes += chunk.length;
        if (receivedBytes <= 2 * 1024 * 1024) chunks.push(chunk);
      });
      response.on("end", () => {
        const text = Buffer.concat(chunks).toString("utf8");
        let value = {};
        try {
          value = text ? JSON.parse(text) : {};
        } catch {
          value = { message: text.slice(0, 500) };
        }
        if ((response.statusCode || 500) < 200 || (response.statusCode || 500) >= 300) {
          reject(new Error(String(value.error || value.message || `Pilot returned HTTP ${response.statusCode}`)));
          return;
        }
        resolve(value);
      });
    });
    request.on("timeout", () => request.destroy(new Error("Pilot did not respond in time")));
    request.on("error", reject);
    if (encodedBody) request.write(encodedBody);
    request.end();
  });
}

async function pilotIsHealthy(timeoutMs = 1100) {
  try {
    const health = await pilotRequestJson("/health", { timeoutMs });
    return Boolean(health && typeof health === "object" && health.ok === true);
  } catch {
    return false;
  }
}

function pilotUnavailableStatus(message = "Pilot is not running on this Mac.") {
  return {
    ok: false,
    service: { state: "unavailable", label: "Pilot unavailable" },
    microphone: { state: "off", label: "Microphone off", confirmed: false },
    tv: { state: "unavailable", label: "TV unavailable", confirmed: false },
    message,
  };
}

async function getPilotControlStatus() {
  if (!(await pilotIsHealthy())) {
    return pilotUnavailableStatus(pilotServiceLastError || "Pilot is not running on this Mac.");
  }

  const [voiceResult, tvResult] = await Promise.allSettled([
    pilotRequestJson("/api/voice", { timeoutMs: 1500 }),
    pilotRequestJson("/api/connection-health", { timeoutMs: 1800 }),
  ]);
  const voice = voiceResult.status === "fulfilled" ? voiceResult.value : null;
  const tv = tvResult.status === "fulfilled" ? tvResult.value : null;
  const microphoneListening = Boolean(
    voice
      && voice.running === true
      && voice.ready === true
      && voice.sleeping !== true
      && voice.activity_state !== "sleeping",
  );
  const tvState = String(tv?.status || "no_tv").toLowerCase();
  const tvConnected = tvState === "connected";
  const tvReconnecting = ["starting", "recovering", "reconnecting"].includes(tvState);

  return {
    ok: true,
    service: { state: "online", label: "Pilot online" },
    microphone: {
      state: microphoneListening ? "listening" : "off",
      label: microphoneListening ? "Microphone listening" : "Microphone off",
      confirmed: microphoneListening,
      detail: voice ? String(voice.error || voice.activity_state || "") : "Voice service unavailable",
    },
    tv: {
      state: tvConnected ? "connected" : tvReconnecting ? "reconnecting" : "unavailable",
      label: tvConnected ? "TV connected" : tvReconnecting ? "TV reconnecting" : "TV unavailable",
      confirmed: tvConnected,
      detail: String(tv?.message || tv?.detail || "No TV connection was confirmed."),
    },
    message: "Pilot is available locally.",
  };
}

function pilotLogTail() {
  try {
    const contents = fs.readFileSync(PILOT_LOG_PATH, "utf8");
    return contents.slice(-1600).trim();
  } catch {
    return "";
  }
}

async function waitForPilotHealth({ timeoutMs = 90000, processRef = null } = {}) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    if (await pilotIsHealthy(1200)) return true;
    if (processRef && processRef.exitCode != null) {
      throw new Error(`Pilot stopped during startup.${pilotLogTail() ? ` ${pilotLogTail()}` : ""}`);
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Pilot did not become healthy within ${Math.round(timeoutMs / 1000)} seconds.${pilotLogTail() ? ` ${pilotLogTail()}` : ""}`);
}

function pilotPortIsOccupied(port = 8766, timeoutMs = 900) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host: "127.0.0.1", port });
    const finish = (occupied) => {
      socket.removeAllListeners();
      socket.destroy();
      resolve(occupied);
    };
    socket.setTimeout(timeoutMs);
    socket.once("connect", () => finish(true));
    socket.once("error", () => finish(false));
    socket.once("timeout", () => finish(false));
  });
}

async function waitForExistingPilotService() {
  // A launch agent, a previous Tessaris window, or a manual start may already
  // be bringing Pilot online.  Wait for that single owner before attempting a
  // new process; otherwise both instances contend for the TV Canvas port.
  if (!(await pilotPortIsOccupied())) return false;
  try {
    return await waitForPilotHealth({ timeoutMs: 15000 });
  } catch {
    return false;
  }
}

async function ensurePilotService() {
  if (await pilotIsHealthy()) {
    pilotServiceLastError = "";
    return getPilotControlStatus();
  }
  if (pilotServiceStartPromise) return pilotServiceStartPromise;

  if (await waitForExistingPilotService()) {
    pilotServiceLastError = "";
    return getPilotControlStatus();
  }

  pilotServiceStartPromise = (async () => {
    const pythonExecutable = path.join(DEV_PROJECT_ROOT, ".venv", "bin", "python");
    if (!fs.existsSync(pythonExecutable)) {
      throw new Error(`Pilot cannot start because its Python runtime is missing: ${pythonExecutable}`);
    }
    fs.mkdirSync(PILOT_RUNTIME_DIR, { recursive: true, mode: 0o700 });
    const logFd = fs.openSync(PILOT_LOG_PATH, "a", 0o600);
    let child;
    try {
      child = spawn(pythonExecutable, [
        "-u",
        "-m",
        "backend.modules.aion_fabric.cli",
        "--runtime-dir",
        PILOT_RUNTIME_DIR,
        "serve",
        "--voice-control",
      ], {
        cwd: DEV_PROJECT_ROOT,
        env: {
          ...process.env,
          PYTHONPATH: [DEV_PROJECT_ROOT, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
        },
        detached: true,
        stdio: ["ignore", logFd, logFd],
      });
      await new Promise((resolve, reject) => {
        child.once("spawn", resolve);
        child.once("error", reject);
      });
    } finally {
      fs.closeSync(logFd);
    }
    pilotServiceProc = child;
    child.once("exit", (code, signal) => {
      if (pilotServiceProc === child) pilotServiceProc = null;
      if (code && code !== 0) {
        pilotServiceLastError = `Pilot stopped with code ${code}${signal ? ` (${signal})` : ""}.`;
      }
    });
    child.unref();
    await waitForPilotHealth({ processRef: child });
    pilotServiceLastError = "";
    return getPilotControlStatus();
  })().catch((error) => {
    pilotServiceLastError = error instanceof Error ? error.message : String(error);
    throw error;
  }).finally(() => {
    pilotServiceStartPromise = null;
  });

  return pilotServiceStartPromise;
}

function showPilotDashboardWindow() {
  if (pilotDashboardWindow && !pilotDashboardWindow.isDestroyed()) {
    if (pilotDashboardWindow.isMinimized()) pilotDashboardWindow.restore();
    pilotDashboardWindow.show();
    pilotDashboardWindow.focus();
    return;
  }

  pilotDashboardWindow = new BrowserWindow({
    width: 1380,
    height: 900,
    minWidth: 980,
    minHeight: 680,
    title: "Pilot Dashboard",
    icon: resolveIconPath(),
    backgroundColor: "#f5f8fc",
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  pilotDashboardWindow.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url);
    return { action: "deny" };
  });
  pilotDashboardWindow.once("ready-to-show", () => {
    pilotDashboardWindow?.show();
    pilotDashboardWindow?.focus();
  });
  pilotDashboardWindow.on("closed", () => {
    pilotDashboardWindow = null;
  });
  void pilotDashboardWindow.loadURL(PILOT_DASHBOARD_URL).catch((error) => {
    pilotServiceLastError = `The Pilot dashboard could not open: ${error.message}`;
  });
}

async function openPilotDashboard() {
  await ensurePilotService();
  showPilotDashboardWindow();
  return { ok: true, status: await getPilotControlStatus(), url: PILOT_DASHBOARD_URL };
}

async function runPilotControl(action = "") {
  await ensurePilotService();
  const routes = {
    "microphone-on": ["/api/voice/resume", null],
    "microphone-off": ["/api/voice/sleep", null],
    "reconnect-tv": ["/api/connection-health/retry", null],
    "open-games": ["/api/dashboard/action", { command: "games", arguments: {} }],
    "open-ai-tv": ["/api/dashboard/action", { command: "aion", arguments: {} }],
  };
  const route = routes[String(action || "")];
  if (!route) throw new Error("Unknown Pilot control");
  const result = await pilotRequestJson(route[0], {
    method: "POST",
    body: route[1],
    timeoutMs: action === "reconnect-tv" ? 12000 : 8000,
  });
  return { ok: true, result, status: await getPilotControlStatus() };
}

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
  path.join(process.resourcesPath || "", "native", "Tessaris Spatial Boardroom.app"),
  path.join(DEV_PROJECT_ROOT, "unity", "spatial-boardroom-mvp", "Builds", "macOS", "Tessaris Spatial Boardroom.app"),
  "/Volumes/Install macOS Sonoma/Tessaris/Unity/spatial-boardroom-mvp/Builds/macOS/Tessaris Spatial Boardroom.app",
].filter(Boolean);

const SPATIAL_BOARDROOM_WEB_CANDIDATES = [
  path.join(process.resourcesPath || "", "boardroom-web"),
  path.join(DEV_PROJECT_ROOT, "unity", "spatial-boardroom-mvp", "Builds", "WebGL"),
].filter(Boolean);

function resolveSpatialBoardroomWebRoot() {
  for (const root of SPATIAL_BOARDROOM_WEB_CANDIDATES) {
    if (fs.existsSync(path.join(root, "index.html"))) return root;
  }
  return null;
}

function spatialBoardroomContentType(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  return ({
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".wasm": "application/wasm",
    ".data": "application/octet-stream",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
  })[extension] || "application/octet-stream";
}

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
    const parsed = new URL(request.url || "/", "http://127.0.0.1");
    if (request.method === "GET" && (parsed.pathname === "/boardroom" || parsed.pathname.startsWith("/boardroom/"))) {
      const webRoot = resolveSpatialBoardroomWebRoot();
      if (!webRoot) {
        response.setHeader("Content-Type", "application/json; charset=utf-8");
        response.writeHead(404); response.end(JSON.stringify({ error: "webgl_build_not_found" })); return;
      }
      const relativePath = decodeURIComponent(parsed.pathname.replace(/^\/boardroom\/?/, "")) || "index.html";
      const resolvedRoot = path.resolve(webRoot);
      const filePath = path.resolve(resolvedRoot, relativePath);
      if (filePath !== resolvedRoot && !filePath.startsWith(`${resolvedRoot}${path.sep}`)) {
        response.setHeader("Content-Type", "application/json; charset=utf-8");
        response.writeHead(403); response.end(JSON.stringify({ error: "forbidden" })); return;
      }
      try {
        const stat = fs.statSync(filePath);
        if (!stat.isFile()) throw new Error("not_file");
        response.setHeader("Content-Type", spatialBoardroomContentType(filePath));
        response.setHeader("Cache-Control", "no-cache");
        response.writeHead(200);
        fs.createReadStream(filePath).pipe(response);
      } catch {
        response.setHeader("Content-Type", "application/json; charset=utf-8");
        response.writeHead(404); response.end(JSON.stringify({ error: "not_found" }));
      }
      return;
    }
    response.setHeader("Content-Type", "application/json; charset=utf-8");
    const authorization = String(request.headers.authorization || "");
    const supplied = authorization.startsWith("Bearer ") ? authorization.slice(7) : "";
    const validToken = supplied.length === token.length
      && crypto.timingSafeEqual(Buffer.from(supplied), Buffer.from(token));
    if (!validToken) {
      response.writeHead(401); response.end(JSON.stringify({ error: "unauthorized" })); return;
    }
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

function readApplicationAccountSession(deviceId, workspaceId) {
  if (!fs.existsSync(APPLICATION_ACCOUNT_DESCRIPTOR_PATH)) return null;
  const descriptor = JSON.parse(fs.readFileSync(APPLICATION_ACCOUNT_DESCRIPTOR_PATH, "utf8"));
  const accountId = String(descriptor?.account_id || "").trim();
  const descriptorWorkspace = String(descriptor?.workspace_id || "").trim();
  const recoveryEpoch = Number(descriptor?.recovery_epoch || 0);
  const activeDevices = Array.isArray(descriptor?.active_devices) ? descriptor.active_devices.map(String) : [];
  if (!/^account_[0-9a-f]{40}$/.test(accountId) || !Number.isSafeInteger(recoveryEpoch) || recoveryEpoch < 1) {
    throw new Error("The application-account recovery descriptor is invalid");
  }
  if (descriptorWorkspace !== workspaceId) {
    throw new Error("The selected workspace does not match the recovered application account");
  }
  if (!activeDevices.includes(deviceId)) {
    throw new Error("This desktop was revoked by application-account recovery");
  }
  return { accountId, recoveryEpoch };
}

function signAionFlowRequest(payload = {}) {
  const method = String(payload.method || "GET").toUpperCase();
  const target = String(payload.target || payload.path || "");
  const body = String(payload.body || "");
  const personId = String(payload.person_id || "").trim();
  const workspaceId = String(payload.workspace_id || "").trim();
  const protectedPrefixes = [
    "/api/workflow-capsules/aion-flow/",
    "/api/aion/business/legal-signing/",
    "/api/aion/business/glyphchain-admin/",
    "/api/aion/business/a2a/",
    "/api/aion/business/project-management/",
  ];
  if (!protectedPrefixes.some((prefix) => target.startsWith(prefix))) {
    throw new Error("AION Flow request target is outside the signed boundary");
  }
  if (!personId || !workspaceId) throw new Error("Select an authenticated Boardroom person and workspace first");
  const key = ensureAionFlowSessionKey();
  const issuedAt = Math.floor(Date.now() / 1000);
  const nonce = crypto.randomBytes(16).toString("hex");
  const deviceId = `tessaris-desktop-${crypto.createHash("sha256").update(key).digest("hex").slice(0, 16)}`;
  const bodyHash = crypto.createHash("sha256").update(body).digest("hex");
  const account = readApplicationAccountSession(deviceId, workspaceId);
  const message = account
    ? ["aion.flow.desktop-session.v2", method, target, bodyHash, deviceId, personId, workspaceId, account.accountId, String(account.recoveryEpoch), String(issuedAt), nonce].join("\n")
    : ["aion.flow.desktop-session.v1", method, target, bodyHash, deviceId, personId, workspaceId, String(issuedAt), nonce].join("\n");
  const signature = crypto.createHmac("sha256", key).update(message).digest("hex");
  const headers = {
    "x-aion-flow-device-id": deviceId,
    "x-aion-flow-person-id": personId,
    "x-aion-flow-workspace-id": workspaceId,
    "x-aion-flow-issued-at": String(issuedAt),
    "x-aion-flow-nonce": nonce,
    "x-aion-flow-body-sha256": bodyHash,
    "x-aion-flow-signature": signature,
  };
  if (account) {
    headers["x-tessaris-account-id"] = account.accountId;
    headers["x-tessaris-recovery-epoch"] = String(account.recoveryEpoch);
  }
  return headers;
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

async function waitForBackendReady({ attempts = 30, delayMs = 1000, processRef = null } = {}) {
  for (let i = 0; i < attempts; i += 1) {
    if (await isBackendHealthy()) {
      return true;
    }
    if (processRef && backendProc !== processRef) {
      return false;
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

function scheduleBackendRestart(detail = "Local backend stopped unexpectedly.") {
  if (isQuitting || backendRestartTimer) return;

  sendBackendStatus({
    ok: false,
    status: "recovering",
    detail,
  });

  backendRestartTimer = setTimeout(async () => {
    backendRestartTimer = null;
    if (isQuitting) return;

    try {
      if (backendStartPromise) {
        await backendStartPromise.catch(() => null);
      }
      if (isQuitting) return;

      const result = await ensureBackendRunning();
      if (result.ok) {
        sendBackendStatus({
          ok: true,
          status: "ready",
          detail: "Local backend recovered automatically.",
        });
      } else {
        scheduleBackendRestart("Local backend recovery did not become ready; retrying.");
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.error(`[backend] automatic restart failed: ${message}`);
      scheduleBackendRestart(`Local backend recovery failed: ${message}`);
    }
  }, 1500);
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
      scheduleBackendRestart(`Local backend could not start: ${error.message}`);
    });

    proc.on("exit", (code, signal) => {
      console.log(`[backend] exited code=${code} signal=${signal}`);

      const wasManaged = backendSpawnedByApp;
      cleanupBackendProcessState();

      if (!isQuitting && wasManaged) {
        scheduleBackendRestart(`Local backend exited (${signal || code || "unknown"}); restarting.`);
      }
    });

    const ready = await waitForBackendReady({
      attempts: 45,
      delayMs: 1000,
      processRef: proc,
    });

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

ipcMain.handle("aion-execute-governed-browser-plan", async (_event, payload = {}) => {
  const grantId = String(payload.grant_id || payload.grantId || "").trim();
  const executionToken = String(payload.execution_token || payload.executionToken || "").trim();
  const workspaceId = String(payload.workspace_id || payload.workspaceId || "").trim();
  if (!grantId || !executionToken) {
    return { ok: false, status: "missing_execution_grant", error: "AION execution grant is required." };
  }

  let authority;
  try {
    authority = await httpPostJson(
      `http://${BACKEND_HOST}:${BACKEND_PORT}/api/local-node/browser-harness/grants/redeem`,
      { grant_id: grantId, execution_token: executionToken, workspace_id: workspaceId || null },
    );
  } catch (error) {
    return { ok: false, status: "execution_grant_rejected", error: String(error?.message || error) };
  }

  const steps = Array.isArray(authority?.steps) ? authority.steps.slice(0, 30) : [];
  const firstNavigation = steps.find((step) => String(step?.operation || "") === "open_page");
  const startUrl = String(firstNavigation?.target?.url || "https://www.google.com/");
  const opened = await openIsolatedBrowserWindow(startUrl, {
    browserProfileId: `aion-governed-${workspaceId || "workspace"}`,
    departmentId: "aion",
    missionId: authority?.plan_id || grantId,
    taskId: grantId,
    activityState: "executing",
    objective: authority?.objective || "Governed browser task",
  });
  if (!opened?.ok) {
    return { ok: false, status: "isolated_browser_unavailable", error: opened?.error || "Could not open isolated browser." };
  }

  const replayPayload = {
    steps,
    inputs: {},
    mode: "live",
    approved_step_ids: Array.isArray(authority?.approved_step_ids) ? authority.approved_step_ids : [],
    approval_payload_hash: String(authority?.approval_payload_hash || ""),
  };
  let result;
  try {
    result = await isolatedBrowserWindow.webContents.executeJavaScript(`
      (async () => {
        for (let attempt = 0; attempt < 50; attempt += 1) {
          if (window.aionIsolatedBrowser?.replaySemanticSteps) {
            return await window.aionIsolatedBrowser.replaySemanticSteps(${JSON.stringify(replayPayload)});
          }
          await new Promise((resolve) => setTimeout(resolve, 100));
        }
        return { ok: false, status: "replay_bridge_unavailable" };
      })()
    `, true);
  } catch (error) {
    result = { ok: false, status: "replay_failed", error: String(error?.message || error) };
  }

  let receipt = null;
  try {
    const recorded = await httpPostJson(
      `http://${BACKEND_HOST}:${BACKEND_PORT}/api/local-node/browser-harness/receipts`,
      { grant_id: grantId, result: result || {}, workspace_id: workspaceId || null },
    );
    receipt = recorded?.receipt || null;
  } catch (error) {
    return {
      ...(result || { ok: false }),
      status: "receipt_recording_failed",
      error: String(error?.message || error),
    };
  }

  return { ...(result || {}), receipt };
});

function runGovernedDesktopProcess(command, args = []) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    child.stdout?.on("data", (chunk) => { stdout += String(chunk || ""); });
    child.stderr?.on("data", (chunk) => { stderr += String(chunk || ""); });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolve({ stdout: stdout.trim(), stderr: stderr.trim() });
      else reject(new Error(stderr.trim() || `Desktop command exited with status ${code}`));
    });
  });
}

function runGovernedAppleScript(lines, args = []) {
  return runGovernedDesktopProcess("/usr/bin/osascript", ["-e", lines.join("\n"), "--", ...args.map((value) => String(value ?? ""))]);
}

let desktopPermissionSetupPromise = null;
function desktopPermissionSetupPath() {
  return path.join(app.getPath("userData"), "desktop-permission-setup-v2.json");
}

function readDesktopPermissionSetup() {
  try {
    return JSON.parse(fs.readFileSync(desktopPermissionSetupPath(), "utf8"));
  } catch {
    return { completed: false };
  }
}

async function prepareDesktopPermissions({ interactive = true, force = false } = {}) {
  const existing = readDesktopPermissionSetup();
  if (!force && existing?.completed === true) return { ok: true, already_prepared: true, ...existing };
  if (desktopPermissionSetupPromise) return desktopPermissionSetupPromise;
  desktopPermissionSetupPromise = (async () => {
    if (interactive) {
      const response = await dialog.showMessageBox(mainWindow || undefined, {
        type: "info",
        title: "Enable Tessaris desktop work",
        message: "Prepare desktop applications once",
        detail: "macOS requires separate permission records for Accessibility, System Events and deeper Notes, Keynote, Pages, Numbers or Mail integration. Tessaris will request them together now so normal desktop work is not interrupted later. macOS may show a few Allow dialogs.",
        buttons: ["Set up now", "Later"],
        defaultId: 0,
        cancelId: 1,
        noLink: true,
      });
      if (response.response !== 0) return { ok: false, status: "permission_setup_deferred" };
    }
    const targets = ["System Events", "Notes", "Keynote", "Pages", "Numbers", "Mail"];
    const results = [{
      app: "Accessibility",
      requested: true,
      ok: process.platform !== "darwin" || systemPreferences.isTrustedAccessibilityClient(true),
    }];
    for (const target of targets) {
      try {
        await runGovernedAppleScript([
          "on run argv",
          "set appName to item 1 of argv",
          "tell application appName to get name",
          "end run",
        ], [target]);
        results.push({ app: target, requested: true, ok: true });
      } catch (error) {
        results.push({ app: target, requested: true, ok: false, error: String(error?.message || error) });
      }
    }
    const record = { completed: true, completed_at: new Date().toISOString(), results };
    fs.writeFileSync(desktopPermissionSetupPath(), JSON.stringify(record, null, 2), { mode: 0o600 });
    return { ok: true, status: "permission_setup_completed", ...record };
  })().finally(() => { desktopPermissionSetupPromise = null; });
  return desktopPermissionSetupPromise;
}

ipcMain.handle("aion-desktop-permissions-status", async () => ({ ok: true, ...readDesktopPermissionSetup() }));
ipcMain.handle("aion-desktop-permissions-prepare", async () => prepareDesktopPermissions({ interactive: true, force: true }));

function genericAxElementLookupLines(actionLines = []) {
  return [
    "set matchedControl to false",
    "set elementList to entire contents of front window",
    "repeat with uiItem in elementList",
    "set candidateText to \"\"",
    "try",
    "set candidateText to name of uiItem as text",
    "end try",
    "if candidateText is \"\" then",
    "try",
    "set candidateText to description of uiItem as text",
    "end try",
    "end if",
    "if candidateText is \"\" then",
    "try",
    "set candidateText to value of attribute \"AXTitle\" of uiItem as text",
    "end try",
    "end if",
    "ignoring case",
    "if candidateText is controlLabel then",
    ...actionLines,
    "set matchedControl to true",
    "exit repeat",
    "end if",
    "end ignoring",
    "end repeat",
    "if matchedControl is false then error \"Control not found: \" & controlLabel",
  ];
}

async function inspectGovernedDesktopApp(appName, maxElements = 80) {
  await runGovernedDesktopProcess("/usr/bin/open", ["-a", appName]);
  const script = [
    "on run argv",
    "set appName to item 1 of argv",
    "set maxItems to (item 2 of argv) as integer",
    "delay 0.2",
    "set outputLines to {}",
    "tell application \"System Events\"",
    "tell process appName",
    "set frontmost to true",
    "if (count windows) is 0 then error \"No visible window for \" & appName",
    "set frontWindow to front window",
    "set end of outputLines to \"window | \" & (name of frontWindow as text)",
    "set elementList to entire contents of frontWindow",
    "set itemCount to 0",
    "repeat with uiItem in elementList",
    "if itemCount is greater than or equal to maxItems then exit repeat",
    "set roleText to \"element\"",
    "set nameText to \"\"",
    "try",
    "set roleText to role of uiItem as text",
    "end try",
    "try",
    "set nameText to name of uiItem as text",
    "end try",
    "if nameText is \"\" then",
    "try",
    "set nameText to description of uiItem as text",
    "end try",
    "end if",
    "if nameText is not \"\" then",
    "set end of outputLines to roleText & \" | \" & nameText",
    "set itemCount to itemCount + 1",
    "end if",
    "end repeat",
    "end tell",
    "end tell",
    "set AppleScript's text item delimiters to linefeed",
    "return outputLines as text",
    "end run",
  ];
  return runGovernedAppleScript(script, [appName, Math.max(10, Math.min(Number(maxElements) || 80, 200))]);
}

function summarizeGovernedDesktopInspection(appName, observation = "") {
  const lines = String(observation || "").split("\n").map((line) => line.trim()).filter(Boolean);
  const pairs = lines.map((line) => {
    const separator = line.indexOf("|");
    return separator < 0
      ? { role: "", name: line }
      : { role: line.slice(0, separator).trim(), name: line.slice(separator + 1).trim() };
  });
  const named = pairs.filter((item) => item.name && item.name.toLowerCase() !== "missing value");
  const uniqueNames = [...new Set(named.map((item) => item.name))];

  if (String(appName || "").toLowerCase() === "calendar") {
    const monthTitle = uniqueNames.find((name) => /^(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}$/i.test(name));
    const dates = named.filter((item) => item.role === "AXList" && /^(?:today,\s*)?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+\d+/i.test(item.name)).map((item) => item.name);
    const range = dates.length ? `${dates[0]} through ${dates[dates.length - 1]}` : "the visible date range";
    const todayAvailable = uniqueNames.some((name) => name.toLowerCase() === "today");
    return [
      `Calendar is open${monthTitle ? ` in ${monthTitle}` : ""}.`,
      `The visible calendar covers ${range}.`,
      `${todayAvailable ? "A Today button is available. " : ""}The window also contains a toolbar, calendar grid, view selector and navigation controls.`,
      "Some icon-only controls do not expose readable accessibility names, so I have not guessed their actions or changed anything.",
    ].join(" ");
  }

  const usefulNames = uniqueNames
    .filter((name) => !/^window$/i.test(name))
    .slice(0, 18);
  return usefulNames.length
    ? `${appName} is open. Visible named controls and content include: ${usefulNames.join(", ")}. No changes were made.`
    : `${appName} is open, but its visible controls did not expose readable accessibility names. No changes were made.`;
}

async function executeGovernedComputerStep(step = {}, approvedStepIds = []) {
  const operation = String(step.operation || "").trim();
  const appName = String(step?.target?.app || "").trim();
  if (!appName || !/^[A-Za-z0-9][A-Za-z0-9 .&+()'_-]{0,119}$/.test(appName)) throw new Error("This desktop app name is not allowed.");
  if (["terminal", "iterm", "iterm2", "script editor", "automator", "shortcuts"].includes(appName.toLowerCase())) {
    throw new Error("This code-execution app is blocked from general desktop automation.");
  }
  if (operation === "open_app") {
    await runGovernedDesktopProcess("/usr/bin/open", ["-a", appName]);
    return { step_id: step.step_id, operation, ok: true, status: "app_opened", app: appName };
  }
  if (operation === "inspect_app") {
    // Newly opened native apps can publish their accessibility tree a moment
    // after the process itself reports as running. Give that tree time to
    // settle, then retry once instead of turning a harmless read-only request
    // into a failed work card.
    await new Promise((resolve) => setTimeout(resolve, 500));
    let inspection;
    try {
      inspection = await inspectGovernedDesktopApp(appName, step.max_elements);
    } catch (error) {
      await new Promise((resolve) => setTimeout(resolve, 900));
      inspection = await inspectGovernedDesktopApp(appName, step.max_elements);
    }
    return {
      step_id: step.step_id,
      operation,
      ok: true,
      status: "app_inspected",
      app: appName,
      observation: inspection.stdout,
      summary: summarizeGovernedDesktopInspection(appName, inspection.stdout),
    };
  }
  if (operation === "wait") {
    const seconds = Math.max(0.1, Math.min(Number(step.seconds) || 1, 10));
    await new Promise((resolve) => setTimeout(resolve, seconds * 1000));
    return { step_id: step.step_id, operation, ok: true, status: "wait_completed", app: appName, seconds };
  }
  if (operation === "verify_text") {
    const inspection = await inspectGovernedDesktopApp(appName, 200);
    const expectedText = String(step.expected_text || "").trim();
    if (!expectedText || !inspection.stdout.toLowerCase().includes(expectedText.toLowerCase())) {
      throw new Error(`Verification failed; text was not visible: ${expectedText || "missing expectation"}`);
    }
    return { step_id: step.step_id, operation, ok: true, status: "text_verified", app: appName, expected_text: expectedText };
  }
  if (step.approval_required === true && ["click_control", "type_text", "select_menu_item", "press_key"].includes(operation) && !approvedStepIds.includes(String(step.step_id || ""))) {
    throw new Error(`Exact approval is required before ${operation.replaceAll("_", " ")}.`);
  }
  if (operation === "click_control") {
    await runGovernedDesktopProcess("/usr/bin/open", ["-a", appName]);
    const script = [
      "on run argv",
      "set appName to item 1 of argv",
      "set controlLabel to item 2 of argv",
      "delay 0.2",
      "tell application \"System Events\"",
      "tell process appName",
      "set frontmost to true",
      ...genericAxElementLookupLines(["perform action \"AXPress\" of uiItem"]),
      "end tell",
      "end tell",
      "return controlLabel",
      "end run",
    ];
    await runGovernedAppleScript(script, [appName, String(step.control || "")]);
    return { step_id: step.step_id, operation, ok: true, status: "control_clicked", app: appName, control: String(step.control || "") };
  }
  if (operation === "type_text") {
    await runGovernedDesktopProcess("/usr/bin/open", ["-a", appName]);
    const useFocusedControl = String(step.control || "").trim().toLowerCase() === "focused control";
    const script = [
      "on run argv",
      "set appName to item 1 of argv",
      "set controlLabel to item 2 of argv",
      "set inputText to item 3 of argv",
      "delay 0.2",
      "tell application \"System Events\"",
      "tell process appName",
      "set frontmost to true",
      ...(useFocusedControl ? [
        "set uiItem to value of attribute \"AXFocusedUIElement\"",
        "try",
        "set roleName to role of uiItem as text",
        "if roleName is \"AXSecureTextField\" then error \"Sensitive fields cannot be automated\"",
        "end try",
        "keystroke \"a\" using command down",
        "keystroke inputText",
      ] : genericAxElementLookupLines([
        "try",
        "set roleName to role of uiItem as text",
        "if roleName is \"AXSecureTextField\" then error \"Sensitive fields cannot be automated\"",
        "end try",
        "try",
        "set value of attribute \"AXFocused\" of uiItem to true",
        "on error",
        "perform action \"AXPress\" of uiItem",
        "end try",
        "keystroke \"a\" using command down",
        "keystroke inputText",
      ])),
      "end tell",
      "end tell",
      "return controlLabel",
      "end run",
    ];
    await runGovernedAppleScript(script, [appName, String(step.control || ""), String(step.value || "")]);
    return { step_id: step.step_id, operation, ok: true, status: "text_typed", app: appName, control: String(step.control || ""), character_count: String(step.value || "").length };
  }
  if (operation === "select_menu_item") {
    await runGovernedDesktopProcess("/usr/bin/open", ["-a", appName]);
    const script = [
      "on run argv",
      "set appName to item 1 of argv",
      "set menuName to item 2 of argv",
      "set itemName to item 3 of argv",
      "delay 0.2",
      "tell application \"System Events\"",
      "tell process appName",
      "set frontmost to true",
      "click menu item itemName of menu 1 of menu bar item menuName of menu bar 1",
      "end tell",
      "end tell",
      "return menuName & \" > \" & itemName",
      "end run",
    ];
    await runGovernedAppleScript(script, [appName, String(step.menu || ""), String(step.item || "")]);
    return { step_id: step.step_id, operation, ok: true, status: "menu_item_selected", app: appName, menu: String(step.menu || ""), item: String(step.item || "") };
  }
  if (operation === "press_key") {
    await runGovernedDesktopProcess("/usr/bin/open", ["-a", appName]);
    const modifiers = Array.isArray(step.modifiers) ? step.modifiers : [];
    const keyCodes = { return: 36, enter: 36, tab: 48, escape: 53, space: 49, delete: 51, backspace: 51, left: 123, right: 124, down: 125, up: 126, home: 115, end: 119, pageup: 116, pagedown: 121 };
    const keyName = String(step.key || "").toLowerCase();
    const keyCode = keyCodes[keyName];
    const script = [
      "on run argv",
      "set appName to item 1 of argv",
      "set keyValue to item 2 of argv",
      "set keyNumber to item 3 of argv",
      "set useCommand to item 4 of argv is \"true\"",
      "set useShift to item 5 of argv is \"true\"",
      "set useOption to item 6 of argv is \"true\"",
      "set useControl to item 7 of argv is \"true\"",
      "tell application \"System Events\"",
      "if useCommand then key down command",
      "if useShift then key down shift",
      "if useOption then key down option",
      "if useControl then key down control",
      "if keyNumber is not \"\" then",
      "key code (keyNumber as integer)",
      "else",
      "keystroke keyValue",
      "end if",
      "if useControl then key up control",
      "if useOption then key up option",
      "if useShift then key up shift",
      "if useCommand then key up command",
      "end tell",
      "return keyValue",
      "end run",
    ];
    await runGovernedAppleScript(script, [appName, keyName.length === 1 ? keyName : "", keyCode == null ? "" : keyCode, modifiers.includes("command"), modifiers.includes("shift"), modifiers.includes("option"), modifiers.includes("control")]);
    return { step_id: step.step_id, operation, ok: true, status: "key_pressed", app: appName, key: keyName, modifiers };
  }
  if (operation === "create_note") {
    if (step.approval_required === true && !approvedStepIds.includes(String(step.step_id || ""))) {
      throw new Error("Exact approval is required before creating a note.");
    }
    const script = [
      "on run argv",
      "set noteTitle to item 1 of argv",
      "set noteBody to item 2 of argv",
      "tell application \"Notes\"",
      "activate",
      "tell default account",
      "set targetFolder to first folder",
      "make new note at targetFolder with properties {name:noteTitle, body:noteBody}",
      "end tell",
      "end tell",
      "return noteTitle",
      "end run",
    ].join("\n");
    await runGovernedDesktopProcess("/usr/bin/osascript", ["-e", script, "--", String(step.title || "Tessaris note"), String(step.value || "")]);
    return { step_id: step.step_id, operation, ok: true, status: "note_created", app: appName, title: String(step.title || "Tessaris note") };
  }
  if (operation === "create_presentation") {
    if (step.approval_required === true && !approvedStepIds.includes(String(step.step_id || ""))) {
      throw new Error("Exact approval is required before creating a presentation.");
    }
    if (appName !== "Keynote") throw new Error("Presentations can only be created in Keynote.");
    const script = [
      "on run argv",
      "set slideTitle to item 1 of argv",
      "set slideBody to item 2 of argv",
      "tell application \"Keynote\"",
      "activate",
      "set newDocument to make new document",
      "tell slide 1 of newDocument",
      "set object text of default title item to slideTitle",
      "set object text of default body item to slideBody",
      "end tell",
      "end tell",
      "return slideTitle",
      "end run",
    ].join("\n");
    await runGovernedDesktopProcess("/usr/bin/osascript", ["-e", script, "--", String(step.title || "New presentation"), String(step.body || "")]);
    return { step_id: step.step_id, operation, ok: true, status: "presentation_created", app: appName, title: String(step.title || "New presentation") };
  }
  if (operation === "create_document") {
    if (appName !== "Pages") throw new Error("Documents can only be created with the Pages recipe.");
    const requestedFileName = String(step.file_name || "").replace(/[^A-Za-z0-9 ._()-]+/g, "").trim().slice(0, 120);
    const outputDirectory = path.join(os.homedir(), "Documents", "Tessaris");
    let outputPath = requestedFileName
      ? path.join(outputDirectory, `${requestedFileName.replace(/\.pages$/i, "")}.pages`)
      : "";
    if (outputPath) {
      fs.mkdirSync(outputDirectory, { recursive: true, mode: 0o700 });
      if (fs.existsSync(outputPath)) {
        const suffix = new Date().toISOString().replace(/[:.]/g, "-");
        outputPath = path.join(outputDirectory, `${requestedFileName.replace(/\.pages$/i, "")} ${suffix}.pages`);
      }
    }
    const script = [
      "on run argv",
      "set documentText to item 1 of argv",
      "set outputPath to item 2 of argv",
      "tell application \"Pages\"",
      "activate",
      "set newDocument to make new document",
      "tell newDocument to set body text to documentText",
      "if outputPath is not \"\" then save newDocument in POSIX file outputPath",
      "end tell",
      "return documentText",
      "end run",
    ];
    await runGovernedAppleScript(script, [String(step.value || ""), outputPath]);
    return {
      step_id: step.step_id,
      operation,
      ok: true,
      status: outputPath ? "document_created_and_saved" : "document_created",
      app: appName,
      character_count: String(step.value || "").length,
      saved_path: outputPath,
    };
  }
  if (operation === "style_document") {
    if (appName !== "Pages") throw new Error("Document styling can only run in Pages.");
    const sourcePath = fs.realpathSync(String(step.file_path || ""));
    if (path.extname(sourcePath).toLowerCase() !== ".pages") {
      throw new Error("The selected document is not a Pages document.");
    }
    const outputDirectory = path.join(os.homedir(), "Documents", "Tessaris");
    fs.mkdirSync(outputDirectory, { recursive: true, mode: 0o700 });
    const baseName = path.basename(sourcePath, path.extname(sourcePath)).replace(/[^A-Za-z0-9 ._()-]+/g, "").trim().slice(0, 100) || "Styled Document";
    let outputPath = path.join(outputDirectory, `${baseName} – Styled.pages`);
    if (fs.existsSync(outputPath)) {
      const suffix = new Date().toISOString().replace(/[:.]/g, "-");
      outputPath = path.join(outputDirectory, `${baseName} – Styled ${suffix}.pages`);
    }
    const script = [
      "on run argv",
      "set sourcePath to item 1 of argv",
      "set outputPath to item 2 of argv",
      "tell application \"Pages\"",
      "activate",
      "set sourceDocument to open POSIX file sourcePath",
      "tell sourceDocument",
      "try",
      "set font of every character of body text to \"Avenir Next\"",
      "set size of every character of body text to 11",
      "end try",
      "try",
      "set font of every character of paragraph 1 of body text to \"Avenir Next Demi Bold\"",
      "set size of every character of paragraph 1 of body text to 26",
      "end try",
      "try",
      "set font of every character of paragraph 2 of body text to \"Avenir Next Medium\"",
      "set size of every character of paragraph 2 of body text to 12",
      "end try",
      "try",
      "repeat with paragraphItem in paragraphs of body text",
      "set paragraphCopy to contents of paragraphItem as text",
      "if paragraphCopy starts with \"1. \" or paragraphCopy starts with \"2. \" or paragraphCopy starts with \"3. \" or paragraphCopy is \"Method\" then",
      "set font of every character of paragraphItem to \"Avenir Next Demi Bold\"",
      "set size of every character of paragraphItem to 15",
      "end if",
      "end repeat",
      "end try",
      "save sourceDocument in POSIX file outputPath",
      "end tell",
      "end tell",
      "return outputPath",
      "end run",
    ];
    await runGovernedAppleScript(script, [sourcePath, outputPath]);
    return {
      step_id: step.step_id,
      operation,
      ok: true,
      status: "document_styled_and_saved",
      app: appName,
      source_path: sourcePath,
      saved_path: outputPath,
    };
  }
  if (operation === "create_spreadsheet") {
    if (appName !== "Numbers") throw new Error("Spreadsheets can only be created with the Numbers recipe.");
    const script = [
      "on run argv",
      "set cellName to item 1 of argv",
      "set cellValue to item 2 of argv",
      "tell application \"Numbers\"",
      "activate",
      "set newDocument to make new document",
      "tell table 1 of sheet 1 of newDocument to set value of cell cellName to cellValue",
      "end tell",
      "return cellName",
      "end run",
    ];
    await runGovernedAppleScript(script, [String(step.cell || "A1"), String(step.value || "")]);
    return { step_id: step.step_id, operation, ok: true, status: "spreadsheet_created", app: appName, cell: String(step.cell || "A1") };
  }
  if (operation === "create_email_draft") {
    if (appName !== "Mail") throw new Error("Email drafts can only be created with the Mail recipe.");
    const script = [
      "on run argv",
      "set draftSubject to item 1 of argv",
      "set draftBody to item 2 of argv",
      "tell application \"Mail\"",
      "activate",
      "make new outgoing message with properties {subject:draftSubject, content:draftBody & return, visible:true}",
      "end tell",
      "return draftSubject",
      "end run",
    ];
    await runGovernedAppleScript(script, [String(step.subject || "Draft email"), String(step.body || "")]);
    return { step_id: step.step_id, operation, ok: true, status: "email_draft_created", app: appName, subject: String(step.subject || "Draft email") };
  }
  throw new Error(`Unsupported governed desktop operation: ${operation || "missing"}`);
}

ipcMain.handle("aion-execute-governed-computer-plan", async (_event, payload = {}) => {
  const grantId = String(payload.grant_id || payload.grantId || "").trim();
  const executionToken = String(payload.execution_token || payload.executionToken || "").trim();
  const workspaceId = String(payload.workspace_id || payload.workspaceId || "").trim();
  if (!grantId || !executionToken) {
    return { ok: false, status: "missing_execution_grant", error: "AION desktop execution grant is required." };
  }
  let authority;
  try {
    authority = await httpPostJson(
      `http://${BACKEND_HOST}:${BACKEND_PORT}/api/local-node/computer-harness/grants/redeem`,
      { grant_id: grantId, execution_token: executionToken, workspace_id: workspaceId || null },
    );
  } catch (error) {
    return { ok: false, status: "execution_grant_rejected", error: String(error?.message || error) };
  }
  const steps = Array.isArray(authority?.steps) ? authority.steps.slice(0, 20) : [];
  const approvedStepIds = Array.isArray(authority?.approved_step_ids) ? authority.approved_step_ids : [];
  const stepResults = [];
  let result;
  try {
    for (const step of steps) stepResults.push(await executeGovernedComputerStep(step, approvedStepIds));
    result = { ok: true, status: "computer_task_completed", steps: stepResults };
  } catch (error) {
    result = { ok: false, status: "computer_task_failed", error: String(error?.message || error), steps: stepResults };
  }
  try {
    const recorded = await httpPostJson(
      `http://${BACKEND_HOST}:${BACKEND_PORT}/api/local-node/computer-harness/receipts`,
      { grant_id: grantId, result, workspace_id: workspaceId || null },
    );
    return { ...result, receipt: recorded?.receipt || null };
  } catch (error) {
    return { ...result, ok: false, status: "receipt_recording_failed", error: String(error?.message || error) };
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

function mainWindowStatePath() {
  return path.join(app.getPath("userData"), "main-window-state.json");
}

function isUsableWindowBounds(bounds) {
  if (!bounds || typeof bounds !== "object") return false;
  const x = Number(bounds.x);
  const y = Number(bounds.y);
  const width = Number(bounds.width);
  const height = Number(bounds.height);
  if (![x, y, width, height].every(Number.isFinite) || width < 800 || height < 600) return false;
  return screen.getAllDisplays().some(({ workArea }) => (
    x < workArea.x + workArea.width - 80
    && x + width > workArea.x + 80
    && y < workArea.y + workArea.height - 80
    && y + height > workArea.y + 80
  ));
}

function readMainWindowState() {
  try {
    const parsed = JSON.parse(fs.readFileSync(mainWindowStatePath(), "utf8"));
    return {
      maximized: parsed?.maximized === true,
      normalBounds: isUsableWindowBounds(parsed?.normalBounds) ? parsed.normalBounds : null,
    };
  } catch {
    // Tessaris is a dashboard shell, so use the full desktop until the user
    // explicitly chooses and saves a smaller window.
    return { maximized: true, normalBounds: null };
  }
}

function writeMainWindowState() {
  if (!app.isReady()) return;
  try {
    const statePath = mainWindowStatePath();
    fs.mkdirSync(path.dirname(statePath), { recursive: true, mode: 0o700 });
    fs.writeFileSync(statePath, JSON.stringify(mainWindowState), { mode: 0o600 });
  } catch (error) {
    console.error("[window] failed to remember the main window state:", error);
  }
}

function scheduleMainWindowStateWrite() {
  if (mainWindowStateWriteTimer) clearTimeout(mainWindowStateWriteTimer);
  mainWindowStateWriteTimer = setTimeout(() => {
    mainWindowStateWriteTimer = null;
    writeMainWindowState();
  }, 180);
}

function restorePreferredMainWindowMode() {
  if (!mainWindow || mainWindow.isDestroyed() || !mainWindowState.maximized) return;
  if (mainWindow.isFullScreen() || mainWindow.isMaximized()) return;
  // macOS can return a zoomed window to its older frame while another app is
  // active. Re-apply the user's chosen zoom state when Tessaris is foregrounded.
  mainWindow.maximize();
}

function createWindow() {
  const iconPath = resolveIconPath();
  mainWindowState = readMainWindowState();
  const rememberedBounds = mainWindowState.normalBounds || {};

  mainWindow = new BrowserWindow({
    width: rememberedBounds.width || 1600,
    height: rememberedBounds.height || 980,
    ...(Number.isFinite(rememberedBounds.x) ? { x: rememberedBounds.x } : {}),
    ...(Number.isFinite(rememberedBounds.y) ? { y: rememberedBounds.y } : {}),
    minWidth: 1280,
    minHeight: 800,
    title: "Tessaris",
    icon: iconPath,
    titleBarStyle: "hiddenInset",
    trafficLightPosition: { x: 18, y: 19 },
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

  mainWindow.once("ready-to-show", () => {
    restorePreferredMainWindowMode();
    setTimeout(() => {
      void prepareDesktopPermissions({ interactive: true });
    }, 1200);
  });

  mainWindow.on("maximize", () => {
    mainWindowState.maximized = true;
    scheduleMainWindowStateWrite();
  });

  mainWindow.on("unmaximize", () => {
    // An unfocused unmaximize can be produced by macOS while switching apps;
    // only treat it as the user's choice when Tessaris is actually active.
    if (mainWindow && !mainWindow.isDestroyed() && mainWindow.isFocused()) {
      mainWindowState.maximized = false;
      scheduleMainWindowStateWrite();
    }
  });

  const rememberNormalBounds = () => {
    if (!mainWindow || mainWindow.isDestroyed()) return;
    if (mainWindow.isMaximized() || mainWindow.isFullScreen() || mainWindowState.maximized) return;
    const bounds = mainWindow.getBounds();
    if (isUsableWindowBounds(bounds)) {
      mainWindowState.normalBounds = bounds;
      scheduleMainWindowStateWrite();
    }
  };
  mainWindow.on("resize", rememberNormalBounds);
  mainWindow.on("move", rememberNormalBounds);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  mainWindow.on("show", () => {
    void ensureMacDockVisible();
  });

  mainWindow.on("blur", () => {
    // Capture the zoomed state before macOS changes window presentation while
    // another application is taking focus.
    if (mainWindow && !mainWindow.isDestroyed() && mainWindow.isMaximized()) {
      mainWindowState.maximized = true;
      writeMainWindowState();
    }
  });

  mainWindow.on("focus", () => {
    void ensureMacDockVisible();
    setTimeout(restorePreferredMainWindowMode, 0);
  });
}

async function ensureMacDockVisible() {
  if (process.platform !== "darwin") return;

  try {
    app.setActivationPolicy("regular");
    await app.dock.show();

    const iconPath = resolveIconPath();
    if (iconPath) {
      app.dock.setIcon(iconPath);
    }
  } catch (error) {
    console.error("[dock] failed to restore the macOS Dock item:", error);
  }
}

const SENTINEL_STATUS_PATH = path.join(os.homedir(), ".tessaris", "security-sentinel", "status.json");
const SENTINEL_POSITION_PATH = path.join(os.homedir(), ".tessaris", "security-sentinel", "window-position.json");

function readSentinelStatus() {
  try {
    const stat = fs.statSync(SENTINEL_STATUS_PATH);
    if (stat.size > 64 * 1024) throw new Error("status_too_large");
    const value = JSON.parse(fs.readFileSync(SENTINEL_STATUS_PATH, "utf8"));
    const heartbeat = Date.parse(String(value.heartbeat_at || ""));
    if (!Number.isFinite(heartbeat) || Date.now() - heartbeat > 30_000) {
      return { state: "offline", detail: "Security Sentinel heartbeat is unavailable." };
    }
    const allowed = new Set(["idle", "observing", "investigating", "review", "urgent", "verified", "offline"]);
    return {
      state: allowed.has(value.state) ? value.state : "offline",
      heartbeat_at: value.heartbeat_at,
      recent_event_count: Number(value.recent_event_count || 0),
      last_event: value.last_event ? {
        title: String(value.last_event.title || "Security event").slice(0, 160),
        severity: String(value.last_event.severity || "LOW").slice(0, 16),
      } : null,
    };
  } catch {
    return { state: "offline", detail: "Security Sentinel is not running." };
  }
}

function positionSentinelWindow() {
  if (!sentinelWindow || sentinelWindow.isDestroyed()) return;
  try {
    const saved = JSON.parse(fs.readFileSync(SENTINEL_POSITION_PATH, "utf8"));
    const savedX = Number(saved?.x);
    const savedY = Number(saved?.y);
    const visible = Number.isFinite(savedX) && Number.isFinite(savedY) && screen.getAllDisplays().some(({ workArea }) => (
      savedX >= workArea.x - 40
      && savedX < workArea.x + workArea.width - 40
      && savedY >= workArea.y - 40
      && savedY < workArea.y + workArea.height - 40
    ));
    if (visible) {
      sentinelWindow.setPosition(Math.round(savedX), Math.round(savedY), false);
      return;
    }
  } catch {
    // Use the default corner until the companion has been moved once.
  }
  const point = screen.getCursorScreenPoint();
  const display = screen.getDisplayNearestPoint(point);
  const { x, y, width, height } = display.workArea;
  const [windowWidth, windowHeight] = sentinelWindow.getSize();
  sentinelWindow.setPosition(x + width - windowWidth - 18, y + height - windowHeight - 18, false);
}

function createSentinelWindow() {
  if (sentinelWindow && !sentinelWindow.isDestroyed()) return sentinelWindow;
  sentinelWindow = new BrowserWindow({
    width: 112, height: 132, transparent: true, frame: false, resizable: false,
    movable: true, alwaysOnTop: true, skipTaskbar: true, hasShadow: false,
    focusable: true, show: false,
    webPreferences: { contextIsolation: true, nodeIntegration: false, preload: path.join(__dirname, "preload.js") },
  });
  sentinelWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  sentinelWindow.loadFile(path.join(__dirname, "aion-sentinel.html"));
  sentinelWindow.once("ready-to-show", () => { positionSentinelWindow(); sentinelWindow.showInactive(); });
  sentinelWindow.on("moved", () => {
    if (!sentinelWindow || sentinelWindow.isDestroyed()) return;
    try {
      fs.mkdirSync(path.dirname(SENTINEL_POSITION_PATH), { recursive: true, mode: 0o700 });
      const [x, y] = sentinelWindow.getPosition();
      fs.writeFileSync(SENTINEL_POSITION_PATH, JSON.stringify({ x, y }), { mode: 0o600 });
    } catch (error) {
      console.error("[sentinel] failed to remember window position:", error);
    }
  });
  sentinelWindow.on("closed", () => { sentinelWindow = null; });
  return sentinelWindow;
}

ipcMain.handle("aion-security-sentinel-status", async () => readSentinelStatus());
ipcMain.handle("aion-security-sentinel-open", async () => {
  if (!mainWindow || mainWindow.isDestroyed()) createWindow();
  mainWindow.show(); mainWindow.focus();
  mainWindow.webContents.send("aion-open-cybersecurity");
  return { ok: true };
});

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

ipcMain.handle("aion-spatial-boardroom-embed", async (_event, payload = {}) => {
  const webRoot = resolveSpatialBoardroomWebRoot();
  if (!webRoot) {
    return {
      ok: false,
      error: "webgl_build_not_found",
      message: "The embedded Spatial Boardroom build is not installed yet.",
      searched: SPATIAL_BOARDROOM_WEB_CANDIDATES,
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
  const origin = `http://127.0.0.1:${bridge.port}`;
  const query = new URLSearchParams({
    "tessaris-endpoint": `${origin}/events`,
    "tessaris-actions": `${origin}/actions`,
    "tessaris-session": bridge.token,
  });
  return {
    ok: true,
    mode: "embedded_webgl",
    status: "ready",
    url: `${origin}/boardroom/?${query.toString()}`,
  };
});

ipcMain.handle("aion-spatial-boardroom-event", async (_event, payload = {}) => {
  if (!spatialBoardroomBridge) return { ok: false, error: "spatial_boardroom_not_running" };
  const event = enqueueSpatialBoardroomEvent(payload);
  return { ok: Boolean(event), event_id: event?.id || null };
});

ipcMain.handle("pilot-control-status", async () => getPilotControlStatus());

ipcMain.handle("pilot-open-dashboard", async () => {
  try {
    return await openPilotDashboard();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    pilotServiceLastError = message;
    return { ok: false, error: "pilot_start_failed", message, status: await getPilotControlStatus() };
  }
});

ipcMain.handle("pilot-control-action", async (_event, rawAction = "") => {
  try {
    return await runPilotControl(String(rawAction || ""));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return { ok: false, error: "pilot_action_failed", message, status: await getPilotControlStatus() };
  }
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

ipcMain.handle("aion-choose-chat-attachments", async () => {
  const owner = BrowserWindow.getFocusedWindow() || mainWindow || undefined;
  const result = await dialog.showOpenDialog(owner, {
    title: "Attach files or folders to AI Chat",
    buttonLabel: "Attach",
    properties: ["openFile", "openDirectory", "multiSelections"],
  });
  if (result.canceled || !result.filePaths?.length) {
    return { ok: false, canceled: true, attachments: [] };
  }
  const attachments = [];
  const errors = [];
  for (const selectedPath of result.filePaths.slice(0, 20)) {
    try {
      const resolvedPath = fs.realpathSync.native ? fs.realpathSync.native(selectedPath) : fs.realpathSync(selectedPath);
      const stats = fs.statSync(resolvedPath);
      if (!stats.isFile() && !stats.isDirectory()) {
        errors.push({ path: selectedPath, error: "unsupported_file_type" });
        continue;
      }
      const extension = path.extname(resolvedPath).toLowerCase().slice(0, 20);
      const packageDocument = stats.isDirectory() && [".pages", ".numbers", ".key", ".rtfd"].includes(extension);
      attachments.push({
        id: crypto.createHash("sha256").update(`${resolvedPath}:${stats.mtimeMs}:${stats.size}`).digest("hex").slice(0, 20),
        path: resolvedPath,
        name: path.basename(resolvedPath),
        kind: stats.isDirectory() && !packageDocument ? "folder" : "file",
        extension,
        size: stats.isFile() ? stats.size : 0,
        modified_at: stats.mtime.toISOString(),
      });
    } catch (error) {
      errors.push({ path: selectedPath, error: String(error?.message || error) });
    }
  }
  return {
    ok: attachments.length > 0,
    canceled: false,
    attachments,
    errors,
    error: attachments.length ? null : "attachments_unavailable",
  };
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

  if (backendRestartTimer) {
    clearTimeout(backendRestartTimer);
    backendRestartTimer = null;
  }

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
  await ensureMacDockVisible();
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
  createSentinelWindow();

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
    await ensureMacDockVisible();
    if (!mainWindow || mainWindow.isDestroyed()) {
      try {
        await ensureBackendRunning();
      } catch (error) {
        console.error("[backend] activate startup failed:", error);
      }
      createWindow();
      createSentinelWindow();

      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.once("did-finish-load", () => {
          void bootBackendForWindow();
        });
      }
    } else {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
      setTimeout(restorePreferredMainWindowMode, 0);
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
