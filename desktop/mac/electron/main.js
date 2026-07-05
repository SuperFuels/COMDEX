const { app, BrowserWindow, ipcMain, globalShortcut, Menu } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");
const http = require("http");
const { pathToFileURL } = require("url");

let mainWindow = null;
let isolatedBrowserWindow = null;
let isolatedBrowserRecording = false;
let captureNextBrowserClick = false;
let captureNextClickArmed = false;

let backendProc = null;
let backendSpawnedByApp = false;
let backendStartPromise = null;
let isQuitting = false;

const DEV_PROJECT_ROOT = "/Users/kevinrobinson/dev/COMDEX";
const BACKEND_HOST = "127.0.0.1";
const BACKEND_PORT = 8080;
const BACKEND_HEALTH_PATH = "/api/local-node/health";
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}${BACKEND_HEALTH_PATH}`;

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
    await isolatedBrowserWindow.webContents.executeJavaScript(
      getRecorderInjectionScript(),
      true,
    );
    return { ok: true };
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
) {
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

    if (!wrapperReady) {
      console.log("[isolated-browser] wrapper missing; reloading isolated-browser.html shell");

      const shellPath = resolveIsolatedBrowserShellPath();
      const webviewPreloadPath = path.join(__dirname, "isolated-webview-preload.js");

      await isolatedBrowserWindow.loadFile(shellPath, {
        query: {
          webviewPreload: webviewPreloadPath,
        },
      });

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
      reloadedWrapper: !wrapperReady,
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
      await runInIsolatedBrowser(
        "window.__AION_BROWSER_RECORDER_START__ && window.__AION_BROWSER_RECORDER_START__()",
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
    },
  });

  isolatedBrowserWindow.webContents.once("did-finish-load", async () => {
    await loadUrlInIsolatedBrowser(startUrl);
  });

  return {
    ok: true,
    reused: false,
    url: startUrl,
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

    console.log(`[backend] project root: ${projectRoot}`);
    console.log(`[backend] python bin: ${pythonBin}`);

    const proc = spawn(pythonBin, [
      "-m",
      "uvicorn",
      "backend.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      "8080",
    ], {
      cwd: projectRoot,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: "1",
        TESSARIS_PROJECT_ROOT: projectRoot,
      },
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

  return await openIsolatedBrowserWindow(startUrl);
});

ipcMain.handle("browser-operator-open-isolated-browser", async (_event, payload = {}) => {
  const startUrl =
    payload.startUrl ||
    payload.url ||
    "https://mail.google.com/mail/u/0/#inbox";

  return await openIsolatedBrowserWindow(startUrl);
});

ipcMain.handle("aion-start-browser-recording", async () => {
  isolatedBrowserRecording = true;

  const injected = await injectBrowserRecorder();

  if (isolatedBrowserWindow && !isolatedBrowserWindow.isDestroyed()) {
    await runInIsolatedBrowser(
      "window.__AION_BROWSER_RECORDER_START__ && window.__AION_BROWSER_RECORDER_START__()",
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
      "window.__AION_BROWSER_RECORDER_STOP__ && window.__AION_BROWSER_RECORDER_STOP__()",
    );
  }

  return {
    ok: true,
    status: "stopped",
    message: "Browser recorder stopped",
    created_at: new Date().toISOString(),
  };
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

app.on("before-quit", async (event) => {
  if (isQuitting) {
    return;
  }

  isQuitting = true;
  event.preventDefault();

  try {
    await stopBackend();
  } finally {
    app.exit(0);
  }
});

app.whenReady().then(() => {
  createWindow();

  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.once("did-finish-load", () => {
      void bootBackendForWindow();
    });
  }

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
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

