const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { fileURLToPath } = require("url");

const TRACE_SCHEMA = "tessaris.business-data-runtime-trace.v1";
const SAFE_TRACE_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const WRITE_FLAGS = new Set(["a", "a+", "as", "as+", "ax", "ax+", "w", "w+", "wx", "wx+"]);

class BusinessDataWriteTracerError extends Error {
  constructor(code) {
    super(code);
    this.name = "BusinessDataWriteTracerError";
    this.code = code;
  }
}

function isWithin(candidate, parent) {
  const relative = path.relative(parent, candidate);
  return relative === "" || (!relative.startsWith(`..${path.sep}`) && relative !== ".." && !path.isAbsolute(relative));
}

function canonicalPath(candidate) {
  const resolved = path.resolve(candidate);
  let cursor = resolved;
  const missing = [];
  while (!fs.existsSync(cursor)) {
    const parent = path.dirname(cursor);
    if (parent === cursor) return resolved;
    missing.unshift(path.basename(cursor));
    cursor = parent;
  }
  let canonical;
  try {
    canonical = fs.realpathSync.native(cursor);
  } catch {
    canonical = cursor;
  }
  return path.join(canonical, ...missing);
}

function normalisePath(rawPath) {
  if (rawPath instanceof URL) {
    if (rawPath.protocol !== "file:") return null;
    return canonicalPath(fileURLToPath(rawPath));
  }
  if (Buffer.isBuffer(rawPath)) return canonicalPath(rawPath.toString("utf8"));
  if (typeof rawPath !== "string" || rawPath.length === 0) return null;
  return canonicalPath(rawPath);
}

function isWriteOpenFlag(flag) {
  if (typeof flag === "number") {
    return Boolean(flag & (fs.constants.O_WRONLY | fs.constants.O_RDWR | fs.constants.O_CREAT
      | fs.constants.O_TRUNC | fs.constants.O_APPEND));
  }
  return WRITE_FLAGS.has(String(flag || "r"));
}

function createBusinessDataWriteTracer({
  sourceRoot,
  applicationRoot,
  updateRoot,
  vaultRoots,
  secretStoreRoots = [],
  pathFingerprintKey,
  maxEvents = 100000,
  fsModule = fs,
} = {}) {
  const fingerprintKey = Buffer.isBuffer(pathFingerprintKey)
    ? Buffer.from(pathFingerprintKey)
    : Buffer.from(String(pathFingerprintKey || ""), "utf8");
  if (fingerprintKey.length < 32) throw new BusinessDataWriteTracerError("trace_fingerprint_key_too_short");
  if (!sourceRoot || !applicationRoot || !updateRoot || !Array.isArray(vaultRoots) || vaultRoots.length === 0
      || !Array.isArray(secretStoreRoots)) {
    throw new BusinessDataWriteTracerError("trace_boundaries_required");
  }

  const roots = {
    source: canonicalPath(sourceRoot),
    application: canonicalPath(applicationRoot),
    update: canonicalPath(updateRoot),
    vaults: vaultRoots.map((item) => canonicalPath(item)),
    secretStores: secretStoreRoots.map((item) => canonicalPath(item)),
  };
  const eventLimit = Math.max(1, Number.parseInt(maxEvents, 10) || 1);
  const events = [];
  const grouped = new Map();
  const originals = [];
  let enabled = false;
  let suspended = false;
  let dropped = 0;

  function destinationClass(destination) {
    if (roots.vaults.some((root) => isWithin(destination, root))) return "business_vault";
    if (roots.secretStores.some((root) => isWithin(destination, root))) return "secret_store";
    if (isWithin(destination, roots.update)) return "update_boundary";
    if (isWithin(destination, roots.application)) return "application_boundary";
    return "external_or_unknown";
  }

  function caller() {
    const ownFile = path.resolve(__filename);
    const stack = String(new Error().stack || "").split("\n").slice(2);
    for (const lineText of stack) {
      const match = lineText.trim().match(/(.+?):(\d+):(\d+)\)?$/);
      if (!match) continue;
      let candidate = match[1].replace(/^at\s+/, "");
      const functionPrefix = candidate.lastIndexOf("(");
      if (functionPrefix >= 0) candidate = candidate.slice(functionPrefix + 1);
      candidate = candidate.replace(/^file:\/\//, "");
      if (candidate.startsWith("node:")) continue;
      candidate = canonicalPath(candidate);
      if (candidate === ownFile || !isWithin(candidate, roots.source)) continue;
      return {
        source_path: path.relative(roots.source, candidate).split(path.sep).join("/"),
        line: Number.parseInt(match[2], 10) || 0,
      };
    }
    return null;
  }

  function record(operation, rawPath) {
    if (!enabled || suspended) return;
    const destination = normalisePath(rawPath);
    if (!destination) return;
    const source = caller();
    if (!source) return;
    const destination_class = destinationClass(destination);
    const destination_hmac_sha256 = crypto
      .createHmac("sha256", fingerprintKey)
      .update(destination, "utf8")
      .digest("hex");
    const groupKey = JSON.stringify([operation, destination_class, source.source_path, source.line]);
    grouped.set(groupKey, (grouped.get(groupKey) || 0) + 1);
    if (events.length >= eventLimit) {
      dropped += 1;
      return;
    }
    events.push({ operation, destination_class, destination_hmac_sha256, ...source });
  }

  function wrap(target, method, operation, pathIndex = 0, predicate = null) {
    if (!target || typeof target[method] !== "function") return;
    const original = target[method];
    originals.push({ target, method, original });
    target[method] = function tracedWrite(...args) {
      if (!predicate || predicate(args)) record(operation, args[pathIndex]);
      return original.apply(this, args);
    };
  }

  function install() {
    if (originals.length > 0) return;
    for (const [method, operation, pathIndex] of [
      ["writeFileSync", "node.fs.write", 0], ["appendFileSync", "node.fs.write", 0],
      ["mkdirSync", "node.fs.mkdir", 0], ["rmSync", "node.fs.remove", 0],
      ["unlinkSync", "node.fs.remove", 0], ["renameSync", "node.fs.rename", 1],
      ["copyFileSync", "node.fs.copy", 1], ["writeFile", "node.fs.write", 0],
      ["appendFile", "node.fs.write", 0], ["mkdir", "node.fs.mkdir", 0],
      ["rm", "node.fs.remove", 0], ["unlink", "node.fs.remove", 0],
      ["rename", "node.fs.rename", 1], ["copyFile", "node.fs.copy", 1],
    ]) wrap(fsModule, method, operation, pathIndex);
    wrap(fsModule, "openSync", "node.fs.open_write", 0, (args) => isWriteOpenFlag(args[1]));
    wrap(fsModule, "open", "node.fs.open_write", 0, (args) => isWriteOpenFlag(args[1]));
    if (fsModule.promises) {
      for (const [method, operation, pathIndex] of [
        ["writeFile", "node.fs.write", 0], ["appendFile", "node.fs.write", 0],
        ["mkdir", "node.fs.mkdir", 0], ["rm", "node.fs.remove", 0],
        ["unlink", "node.fs.remove", 0], ["rename", "node.fs.rename", 1],
        ["copyFile", "node.fs.copy", 1],
      ]) wrap(fsModule.promises, method, operation, pathIndex);
      wrap(fsModule.promises, "open", "node.fs.open_write", 0, (args) => isWriteOpenFlag(args[1]));
    }
  }

  function uninstall() {
    while (originals.length > 0) {
      const { target, method, original } = originals.pop();
      target[method] = original;
    }
  }

  function start() {
    if (enabled) throw new BusinessDataWriteTracerError("trace_already_active");
    install();
    enabled = true;
  }

  function stop() {
    enabled = false;
    uninstall();
  }

  function report({ sessionId, scenario, scenarioCompleted = true, surface = "electron_main" } = {}) {
    if (!SAFE_TRACE_ID.test(String(sessionId || "")) || !SAFE_TRACE_ID.test(String(scenario || ""))) {
      throw new BusinessDataWriteTracerError("trace_session_identity_required");
    }
    if (!SAFE_TRACE_ID.test(String(surface || ""))) {
      throw new BusinessDataWriteTracerError("trace_surface_identity_required");
    }
    const destinationCounts = {};
    for (const event of events) {
      destinationCounts[event.destination_class] = (destinationCounts[event.destination_class] || 0) + 1;
    }
    const groupedSourceOperations = [...grouped.entries()].map(([key, count]) => {
      const [operation, destination_class, source_path, line] = JSON.parse(key);
      return { operation, destination_class, source_path, line, count };
    }).sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
    const unsafeWriteCount = Object.entries(destinationCounts)
      .filter(([destination]) => !["business_vault", "secret_store"].includes(destination))
      .reduce((total, [, count]) => total + count, 0);
    return {
      schema_version: TRACE_SCHEMA,
      session_id: String(sessionId),
      scenario: String(scenario),
      surface: String(surface),
      evidence_kind: "process_write_observations",
      privacy: "source_locations_and_keyed_path_fingerprints_only_no_raw_paths_or_values",
      event_count: events.length,
      scenario_completed: Boolean(scenarioCompleted),
      dropped_event_count: dropped,
      complete: Boolean(scenarioCompleted) && dropped === 0,
      destination_counts: Object.fromEntries(Object.entries(destinationCounts).sort()),
      unsafe_write_count: unsafeWriteCount,
      release_gate_passed: events.length > 0 && Boolean(scenarioCompleted) && dropped === 0 && unsafeWriteCount === 0,
      grouped_source_operations: groupedSourceOperations,
      events: events.map((event) => ({ ...event })),
    };
  }

  function writeReport(reportPath, options = {}) {
    const payload = report(options);
    suspended = true;
    try {
      fs.mkdirSync(path.dirname(reportPath), { recursive: true, mode: 0o700 });
      fs.writeFileSync(reportPath, `${JSON.stringify(payload, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
      fs.chmodSync(reportPath, 0o600);
    } finally {
      suspended = false;
    }
    return payload;
  }

  return { start, stop, report, writeReport };
}

module.exports = {
  BusinessDataWriteTracerError,
  TRACE_SCHEMA,
  createBusinessDataWriteTracer,
};
