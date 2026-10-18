const fs = require("fs");
const path = require("path");

class DesktopRuntimeConfigurationError extends Error {
  constructor(code) {
    super(code);
    this.name = "DesktopRuntimeConfigurationError";
    this.code = code;
  }
}

function resolveBackendPort(value, fallback = 8080) {
  const raw = String(value ?? "").trim();
  if (!raw) return fallback;
  if (!/^\d{1,5}$/.test(raw)) {
    throw new DesktopRuntimeConfigurationError("desktop_backend_port_invalid");
  }
  const port = Number.parseInt(raw, 10);
  if (port < 1 || port > 65535) {
    throw new DesktopRuntimeConfigurationError("desktop_backend_port_invalid");
  }
  return port;
}

function isFilesystemRoot(candidate) {
  const resolved = path.resolve(candidate);
  return resolved === path.parse(resolved).root;
}

function resolveDiscoveryUserDataPath(value) {
  const raw = String(value ?? "").trim();
  if (!raw) return null;
  if (!path.isAbsolute(raw) || isFilesystemRoot(raw)) {
    throw new DesktopRuntimeConfigurationError("desktop_user_data_path_unsafe");
  }
  const resolved = path.resolve(raw);
  fs.mkdirSync(resolved, { recursive: true, mode: 0o700 });
  fs.chmodSync(resolved, 0o700);
  return resolved;
}

function resolveDesktopRuntimeConfiguration(env = process.env, defaultLockPath) {
  const discoveryMode = env.TESSARIS_DISCOVERY_MODE === "1";
  const userDataPath = resolveDiscoveryUserDataPath(
    env.TESSARIS_DESKTOP_USER_DATA_DIR,
  );
  if (userDataPath && !discoveryMode) {
    throw new DesktopRuntimeConfigurationError(
      "desktop_custom_user_data_requires_discovery_mode",
    );
  }
  if (discoveryMode && !userDataPath) {
    throw new DesktopRuntimeConfigurationError(
      "desktop_discovery_user_data_required",
    );
  }
  return {
    backendPort: resolveBackendPort(env.TESSARIS_BACKEND_PORT),
    discoveryMode,
    userDataPath,
    instanceLockPath: userDataPath
      ? path.join(userDataPath, "desktop-instance.pid")
      : defaultLockPath,
  };
}

function resolveDiscoveryAutostart(env = process.env) {
  const sessionId = String(env.TESSARIS_DISCOVERY_AUTOSTART_SESSION || "").trim();
  const scenario = String(env.TESSARIS_DISCOVERY_AUTOSTART_SCENARIO || "").trim();
  if (!sessionId && !scenario) return null;
  if (env.TESSARIS_DISCOVERY_MODE !== "1") {
    throw new DesktopRuntimeConfigurationError("desktop_discovery_autostart_requires_discovery_mode");
  }
  const safe = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
  if (!safe.test(sessionId) || !safe.test(scenario)) {
    throw new DesktopRuntimeConfigurationError("desktop_discovery_autostart_invalid");
  }
  return { sessionId, scenario };
}

module.exports = {
  DesktopRuntimeConfigurationError,
  resolveBackendPort,
  resolveDiscoveryAutostart,
  resolveDesktopRuntimeConfiguration,
  resolveDiscoveryUserDataPath,
};
