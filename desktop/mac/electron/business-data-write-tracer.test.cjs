const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { createBusinessDataWriteTracer } = require("./business-data-write-tracer");

test("Electron tracer emits content-free Vault evidence and restores fs", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tessaris-electron-trace-"));
  const sourceRoot = path.join(root, "source");
  const applicationRoot = path.join(root, "application");
  const updateRoot = path.join(root, "updates");
  const vaultRoot = path.join(root, "vault");
  const evidenceRoot = path.join(root, "evidence");
  for (const target of [sourceRoot, applicationRoot, updateRoot, vaultRoot, evidenceRoot]) {
    fs.mkdirSync(target, { recursive: true });
  }
  const helperPath = path.join(sourceRoot, "scenario.cjs");
  fs.writeFileSync(helperPath, `module.exports = (fs, target) => fs.writeFileSync(target, "SECRET CUSTOMER VALUE");\n`);
  const scenarioWrite = require(helperPath);
  const originalWrite = fs.writeFileSync;
  const tracer = createBusinessDataWriteTracer({
    sourceRoot,
    applicationRoot,
    updateRoot,
    vaultRoots: [vaultRoot],
    pathFingerprintKey: Buffer.alloc(32, 7),
  });
  try {
    tracer.start();
    scenarioWrite(fs, path.join(vaultRoot, "record.bin"));
    tracer.stop();
    assert.equal(fs.writeFileSync, originalWrite);
    const reportPath = path.join(evidenceRoot, "business-map-and-departments.electron_main.json");
    const report = tracer.writeReport(reportPath, {
      sessionId: "business-map-and-departments",
      scenario: "business-map-and-departments",
      scenarioCompleted: true,
    });
    assert.equal(report.release_gate_passed, true);
    assert.equal(report.destination_counts.business_vault, 1);
    const encoded = fs.readFileSync(reportPath, "utf8");
    assert.equal(encoded.includes("SECRET CUSTOMER VALUE"), false);
    assert.equal(encoded.includes(path.join(vaultRoot, "record.bin")), false);
    assert.match(report.events[0].destination_hmac_sha256, /^[a-f0-9]{64}$/);
    assert.equal(report.events[0].source_path, "scenario.cjs");
  } finally {
    try { tracer.stop(); } catch {}
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("Electron tracer fails unsafe and incomplete scenarios closed", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tessaris-electron-trace-"));
  const sourceRoot = path.join(root, "source");
  const applicationRoot = path.join(root, "application");
  const updateRoot = path.join(root, "updates");
  const vaultRoot = path.join(root, "vault");
  for (const target of [sourceRoot, applicationRoot, updateRoot, vaultRoot]) fs.mkdirSync(target, { recursive: true });
  const helperPath = path.join(sourceRoot, "scenario.cjs");
  fs.writeFileSync(helperPath, `module.exports = (fs, target) => fs.writeFileSync(target, "value");\n`);
  const scenarioWrite = require(helperPath);
  const tracer = createBusinessDataWriteTracer({
    sourceRoot, applicationRoot, updateRoot, vaultRoots: [vaultRoot], pathFingerprintKey: Buffer.alloc(32, 9),
  });
  try {
    tracer.start();
    scenarioWrite(fs, path.join(applicationRoot, "customer.json"));
    tracer.stop();
    const report = tracer.report({
      sessionId: "business-map-and-departments",
      scenario: "business-map-and-departments",
      scenarioCompleted: false,
    });
    assert.equal(report.scenario_completed, false);
    assert.equal(report.complete, false);
    assert.equal(report.unsafe_write_count, 1);
    assert.equal(report.release_gate_passed, false);
  } finally {
    try { tracer.stop(); } catch {}
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("Electron tracer allows only explicitly bounded secret-store writes", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tessaris-electron-secret-trace-"));
  const sourceRoot = path.join(root, "source");
  const applicationRoot = path.join(root, "application");
  const updateRoot = path.join(root, "updates");
  const vaultRoot = path.join(root, "vault");
  const secretRoot = path.join(root, "security");
  for (const target of [sourceRoot, applicationRoot, updateRoot, vaultRoot, secretRoot]) {
    fs.mkdirSync(target, { recursive: true });
  }
  const helperPath = path.join(sourceRoot, "scenario.cjs");
  fs.writeFileSync(helperPath, `module.exports = (fs, target) => fs.writeFileSync(target, "SECRET");\n`);
  const scenarioWrite = require(helperPath);
  const tracer = createBusinessDataWriteTracer({
    sourceRoot, applicationRoot, updateRoot, vaultRoots: [vaultRoot],
    secretStoreRoots: [secretRoot], pathFingerprintKey: Buffer.alloc(32, 4),
  });
  try {
    tracer.start();
    scenarioWrite(fs, path.join(secretRoot, "desktop-session.key"));
    tracer.stop();
    const report = tracer.report({ sessionId: "identity-access", scenario: "identity-access" });
    assert.deepEqual(report.destination_counts, { secret_store: 1 });
    assert.equal(report.unsafe_write_count, 0);
    assert.equal(report.release_gate_passed, true);
  } finally {
    try { tracer.stop(); } catch {}
    fs.rmSync(root, { recursive: true, force: true });
  }
});
