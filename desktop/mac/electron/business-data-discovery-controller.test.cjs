const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { createBusinessDataDiscoveryController } = require("./business-data-discovery-controller");

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tessaris-electron-controller-"));
  const paths = Object.fromEntries(["source", "application", "updates", "vault", "evidence"].map((name) => {
    const target = path.join(root, name);
    fs.mkdirSync(target, { recursive: true });
    return [name, target];
  }));
  const manifest = path.join(root, "manifest.json");
  fs.writeFileSync(manifest, JSON.stringify({
    required_discovery_sessions: [{ id: "identity-access", name: "Identity" }],
  }));
  const catalogue = path.join(root, "scenarios.json");
  fs.writeFileSync(catalogue, JSON.stringify({
    scenarios: [{
      session_id: "identity-access",
      execution_surfaces: ["electron_main", "desktop_renderer"],
      expected_external_classes: ["secret_store"],
    }],
  }));
  const helper = path.join(paths.source, "scenario.cjs");
  fs.writeFileSync(helper, `module.exports = (fs, target) => fs.writeFileSync(target, "PRIVATE");\n`);
  return { root, paths, manifest, catalogue, write: require(helper) };
}

function rendererOnlyFixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tessaris-renderer-controller-"));
  const paths = Object.fromEntries(["source", "application", "updates", "vault", "evidence"].map((name) => {
    const target = path.join(root, name);
    fs.mkdirSync(target, { recursive: true });
    return [name, target];
  }));
  const manifest = path.join(root, "manifest.json");
  fs.writeFileSync(manifest, JSON.stringify({
    required_discovery_sessions: [{ id: "business-onboarding", name: "Onboarding" }],
  }));
  const catalogue = path.join(root, "scenarios.json");
  fs.writeFileSync(catalogue, JSON.stringify({
    scenarios: [{
      session_id: "business-onboarding",
      execution_surfaces: ["desktop_renderer", "desktop_backend"],
      expected_external_classes: ["secret_store"],
    }],
  }));
  return { root, paths, manifest, catalogue };
}

test("controller requires a secret and emits content-free Electron and renderer fragments", () => {
  const item = fixture();
  const token = "x".repeat(32);
  const controller = createBusinessDataDiscoveryController({
    manifestPath: item.manifest,
    scenarioCataloguePath: item.catalogue,
    traceRoot: item.paths.evidence,
    sourceRoot: item.paths.source,
    applicationRoot: item.paths.application,
    updateRoot: item.paths.updates,
    vaultRoots: [item.paths.vault],
    pathFingerprintKey: Buffer.alloc(32, 5),
    controlToken: token,
    externalClassProbe: () => ["secret_store"],
  });
  try {
    assert.throws(() => controller.status({ token: "wrong" }), /discovery_control_unauthorised/);
    controller.start({ token, sessionId: "identity-access", scenario: "identity-access" });
    item.write(fs, path.join(item.paths.vault, "identity.bin"));
    controller.recordRendererStorage({
      operation: "set",
      storageArea: "local",
      key: "private-customer-key",
    });
    const result = controller.stop({ token, scenarioCompleted: true });
    assert.equal(result.release_gate_passed, false);
    assert.equal(result.fragment_name, "identity-access.electron_main.json");
    assert.deepEqual(result.fragment_names, [
      "identity-access.electron_main.json",
      "identity-access.desktop_renderer.json",
    ]);
    const encoded = fs.readFileSync(path.join(item.paths.evidence, result.fragment_name), "utf8");
    assert.equal(encoded.includes("PRIVATE"), false);
    assert.equal(encoded.includes(path.join(item.paths.vault, "identity.bin")), false);
    const renderer = fs.readFileSync(
      path.join(item.paths.evidence, "identity-access.desktop_renderer.json"),
      "utf8",
    );
    assert.equal(renderer.includes("private-customer-key"), false);
    assert.equal(JSON.parse(renderer).release_gate_passed, false);
    assert.match(JSON.parse(renderer).events[0].destination_hmac_sha256, /^[a-f0-9]{64}$/);
  } finally {
    fs.rmSync(item.root, { recursive: true, force: true });
  }
});

test("controller rejects trace roots overlapping app, updater or Vault", () => {
  const item = fixture();
  try {
    assert.throws(() => createBusinessDataDiscoveryController({
      manifestPath: item.manifest,
      scenarioCataloguePath: item.catalogue,
      traceRoot: path.join(item.paths.vault, "evidence"),
      sourceRoot: item.paths.source,
      applicationRoot: item.paths.application,
      updateRoot: item.paths.updates,
      vaultRoots: [item.paths.vault],
      pathFingerprintKey: Buffer.alloc(32, 5),
      controlToken: "x".repeat(32),
    }), /discovery_trace_root_overlap/);
  } finally {
    fs.rmSync(item.root, { recursive: true, force: true });
  }
});

test("renderer-only journeys emit renderer evidence without inventing Electron evidence", () => {
  const item = rendererOnlyFixture();
  const token = "r".repeat(32);
  const controller = createBusinessDataDiscoveryController({
    manifestPath: item.manifest,
    scenarioCataloguePath: item.catalogue,
    traceRoot: item.paths.evidence,
    sourceRoot: item.paths.source,
    applicationRoot: item.paths.application,
    updateRoot: item.paths.updates,
    vaultRoots: [item.paths.vault],
    pathFingerprintKey: Buffer.alloc(32, 7),
    controlToken: token,
    externalClassProbe: () => ["secret_store"],
  });
  try {
    controller.start({
      token,
      sessionId: "business-onboarding",
      scenario: "create-business-through-onboarding-pilot",
    });
    const result = controller.stop({ token, scenarioCompleted: true });

    assert.equal(result.fragment_name, null);
    assert.deepEqual(result.fragment_names, ["business-onboarding.desktop_renderer.json"]);
    assert.equal(result.unsafe_write_count, 0);
    assert.equal(result.release_gate_passed, true);
    assert.equal(
      fs.existsSync(path.join(item.paths.evidence, "business-onboarding.electron_main.json")),
      false,
    );
    const renderer = JSON.parse(fs.readFileSync(
      path.join(item.paths.evidence, "business-onboarding.desktop_renderer.json"),
      "utf8",
    ));
    assert.equal(renderer.complete, true);
    assert.equal(renderer.release_gate_passed, true);
    assert.equal(renderer.event_count, 0);
  } finally {
    fs.rmSync(item.root, { recursive: true, force: true });
  }
});

test("renderer evidence approves only shared content-free preferences and browser purges", () => {
  const item = rendererOnlyFixture();
  const token = "p".repeat(32);
  const controller = createBusinessDataDiscoveryController({
    manifestPath: item.manifest,
    scenarioCataloguePath: item.catalogue,
    traceRoot: item.paths.evidence,
    sourceRoot: item.paths.source,
    applicationRoot: item.paths.application,
    updateRoot: item.paths.updates,
    vaultRoots: [item.paths.vault],
    pathFingerprintKey: Buffer.alloc(32, 9),
    controlToken: token,
    externalClassProbe: () => ["secret_store"],
  });
  try {
    controller.start({ token, sessionId: "business-onboarding", scenario: "onboarding" });
    controller.recordRendererStorage({ operation: "set", storageArea: "local", key: "aion.activeTab.v1" });
    controller.recordRendererStorage({ operation: "remove", storageArea: "local", key: "legacy-private-record" });
    const result = controller.stop({ token, scenarioCompleted: true });
    assert.equal(result.release_gate_passed, true);
    assert.equal(result.unsafe_write_count, 0);
    const report = JSON.parse(fs.readFileSync(
      path.join(item.paths.evidence, "business-onboarding.desktop_renderer.json"), "utf8",
    ));
    assert.deepEqual(report.destination_counts, {
      approved_browser_purge: 1,
      approved_interface_state: 1,
    });
    assert.equal(JSON.stringify(report).includes("legacy-private-record"), false);
    assert.equal(JSON.stringify(report).includes("aion.activeTab.v1"), false);
    assert.deepEqual(report.observed_external_classes, ["secret_store"]);
  } finally {
    fs.rmSync(item.root, { recursive: true, force: true });
  }
});

test("controller fails closed when a required external class is not observed", () => {
  const item = rendererOnlyFixture();
  const token = "s".repeat(32);
  const controller = createBusinessDataDiscoveryController({
    manifestPath: item.manifest,
    scenarioCataloguePath: item.catalogue,
    traceRoot: item.paths.evidence,
    sourceRoot: item.paths.source,
    applicationRoot: item.paths.application,
    updateRoot: item.paths.updates,
    vaultRoots: [item.paths.vault],
    pathFingerprintKey: Buffer.alloc(32, 11),
    controlToken: token,
    externalClassProbe: () => [],
  });
  try {
    controller.start({ token, sessionId: "business-onboarding", scenario: "onboarding" });
    const result = controller.stop({ token, scenarioCompleted: true });
    assert.equal(result.release_gate_passed, false);
    const report = JSON.parse(fs.readFileSync(
      path.join(item.paths.evidence, "business-onboarding.desktop_renderer.json"), "utf8",
    ));
    assert.deepEqual(report.observed_external_classes, []);
  } finally {
    fs.rmSync(item.root, { recursive: true, force: true });
  }
});
