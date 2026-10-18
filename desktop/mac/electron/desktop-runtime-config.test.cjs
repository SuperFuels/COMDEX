const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const {
  resolveBackendPort,
  resolveDiscoveryAutostart,
  resolveDesktopRuntimeConfiguration,
} = require("./desktop-runtime-config");

test("backend port accepts a valid isolated loopback port", () => {
  assert.equal(resolveBackendPort("8180"), 8180);
  assert.equal(resolveBackendPort(""), 8080);
});

test("backend port rejects malformed or out-of-range values", () => {
  for (const value of ["0", "65536", "80x", "-1", "1.5"]) {
    assert.throws(
      () => resolveBackendPort(value),
      { message: "desktop_backend_port_invalid" },
    );
  }
});

test("discovery profile receives its own user data and process lock", (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tessaris-desktop-profile-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const configuration = resolveDesktopRuntimeConfiguration({
    TESSARIS_DISCOVERY_MODE: "1",
    TESSARIS_DESKTOP_USER_DATA_DIR: root,
    TESSARIS_BACKEND_PORT: "8180",
  }, "/tmp/live-tessaris.pid");
  assert.equal(configuration.backendPort, 8180);
  assert.equal(configuration.userDataPath, root);
  assert.equal(configuration.instanceLockPath, path.join(root, "desktop-instance.pid"));
  assert.equal(fs.statSync(root).mode & 0o777, 0o700);
});

test("discovery refuses to share the live desktop profile", () => {
  assert.throws(
    () => resolveDesktopRuntimeConfiguration({ TESSARIS_DISCOVERY_MODE: "1" }, "/tmp/live.pid"),
    { message: "desktop_discovery_user_data_required" },
  );
  assert.throws(
    () => resolveDesktopRuntimeConfiguration({
      TESSARIS_DISCOVERY_MODE: "0",
      TESSARIS_DESKTOP_USER_DATA_DIR: "/tmp/tessaris-unexpected-profile",
    }, "/tmp/live.pid"),
    { message: "desktop_custom_user_data_requires_discovery_mode" },
  );
});

test("desktop launcher passes the configured backend port to uvicorn", () => {
  const source = fs.readFileSync(path.join(__dirname, "main.js"), "utf8");
  assert.match(source, /"--port",\s*String\(BACKEND_PORT\)/);
  assert.doesNotMatch(source, /"--port",\s*"8080"/);
});

test("discovery launcher suppresses the always-on-top security companion", () => {
  const source = fs.readFileSync(path.join(__dirname, "main.js"), "utf8");
  assert.match(
    source,
    /function createSentinelWindow\(\) \{\s*\/\/[\s\S]*?if \(DESKTOP_RUNTIME_CONFIGURATION\.discoveryMode\) return null;/,
  );
});

test("discovery autostart requires a complete safe discovery-only contract", () => {
  assert.equal(resolveDiscoveryAutostart({}), null);
  assert.deepEqual(resolveDiscoveryAutostart({
    TESSARIS_DISCOVERY_MODE: "1",
    TESSARIS_DISCOVERY_AUTOSTART_SESSION: "business-onboarding",
    TESSARIS_DISCOVERY_AUTOSTART_SCENARIO: "create-business-through-onboarding-pilot",
  }), {
    sessionId: "business-onboarding",
    scenario: "create-business-through-onboarding-pilot",
  });
  assert.throws(() => resolveDiscoveryAutostart({
    TESSARIS_DISCOVERY_MODE: "0",
    TESSARIS_DISCOVERY_AUTOSTART_SESSION: "business-onboarding",
    TESSARIS_DISCOVERY_AUTOSTART_SCENARIO: "create-business-through-onboarding-pilot",
  }), { message: "desktop_discovery_autostart_requires_discovery_mode" });
  assert.throws(() => resolveDiscoveryAutostart({
    TESSARIS_DISCOVERY_MODE: "1",
    TESSARIS_DISCOVERY_AUTOSTART_SESSION: "business-onboarding",
  }), { message: "desktop_discovery_autostart_invalid" });
});
