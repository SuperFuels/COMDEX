const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const {
  createBusinessDataWriteTracer,
} = require("./business-data-write-tracer");
const {
  isAllowedKey: isApprovedRendererPreference,
} = require("../src/desktop-preference-policy");

class BusinessDataDiscoveryControllerError extends Error {
  constructor(code) {
    super(code);
    this.name = "BusinessDataDiscoveryControllerError";
    this.code = code;
  }
}

function isWithin(candidate, parent) {
  const relative = path.relative(path.resolve(parent), path.resolve(candidate));
  return relative === "" || (!relative.startsWith(`..${path.sep}`) && relative !== ".." && !path.isAbsolute(relative));
}

function assertSeparated(traceRoot, protectedRoots) {
  for (const protectedRoot of protectedRoots) {
    if (isWithin(traceRoot, protectedRoot) || isWithin(protectedRoot, traceRoot)) {
      throw new BusinessDataDiscoveryControllerError("discovery_trace_root_overlap");
    }
  }
}

function readRequiredSessions(manifestPath) {
  let payload;
  try {
    payload = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  } catch {
    throw new BusinessDataDiscoveryControllerError("discovery_manifest_invalid");
  }
  const sessions = Array.isArray(payload.required_discovery_sessions)
    ? payload.required_discovery_sessions.map((item) => String(item?.id || "")).filter(Boolean)
    : [];
  if (sessions.length === 0 || new Set(sessions).size !== sessions.length) {
    throw new BusinessDataDiscoveryControllerError("discovery_manifest_sessions_invalid");
  }
  return new Set(sessions);
}

function readSupportedDesktopSessions(cataloguePath, requiredSessions) {
  let payload;
  try {
    payload = JSON.parse(fs.readFileSync(cataloguePath, "utf8"));
  } catch {
    throw new BusinessDataDiscoveryControllerError("discovery_scenario_catalogue_invalid");
  }
  const rows = Array.isArray(payload.scenarios) ? payload.scenarios : [];
  const supported = new Map();
  for (const row of rows) {
    const sessionId = String(row?.session_id || "");
    const surfaces = Array.isArray(row?.execution_surfaces) ? row.execution_surfaces : [];
    if (requiredSessions.has(sessionId)
        && (surfaces.includes("electron_main") || surfaces.includes("desktop_renderer"))) {
      supported.set(sessionId, {
        surfaces: new Set(surfaces),
        expectedExternalClasses: new Set(
          (Array.isArray(row?.expected_external_classes) ? row.expected_external_classes : [])
            .map((item) => String(item || ""))
            .filter((item) => item && item !== "none"),
        ),
      });
    }
  }
  if (supported.size === 0) {
    throw new BusinessDataDiscoveryControllerError("discovery_desktop_sessions_missing");
  }
  return supported;
}

function secureTokenMatches(expected, supplied) {
  const left = Buffer.from(String(expected || ""), "utf8");
  const right = Buffer.from(String(supplied || ""), "utf8");
  return left.length === right.length && left.length >= 32 && crypto.timingSafeEqual(left, right);
}

function createBusinessDataDiscoveryController({
  manifestPath,
  scenarioCataloguePath,
  traceRoot,
  sourceRoot,
  applicationRoot,
  updateRoot,
  vaultRoots,
  secretStoreRoots = [],
  pathFingerprintKey,
  controlToken,
  surface = "electron_main",
  maxEvents = 100000,
  externalClassProbe = null,
} = {}) {
  if (String(controlToken || "").length < 32) {
    throw new BusinessDataDiscoveryControllerError("discovery_control_token_too_short");
  }
  const fingerprintKey = Buffer.isBuffer(pathFingerprintKey)
    ? Buffer.from(pathFingerprintKey)
    : Buffer.from(String(pathFingerprintKey || ""), "utf8");
  if (fingerprintKey.length < 32) {
    throw new BusinessDataDiscoveryControllerError("trace_fingerprint_key_too_short");
  }
  if (!manifestPath || !scenarioCataloguePath || !traceRoot || !sourceRoot || !applicationRoot || !updateRoot
      || !Array.isArray(vaultRoots) || vaultRoots.length === 0 || !Array.isArray(secretStoreRoots)) {
    throw new BusinessDataDiscoveryControllerError("discovery_configuration_incomplete");
  }
  const resolved = {
    manifest: path.resolve(manifestPath),
    trace: path.resolve(traceRoot),
    source: path.resolve(sourceRoot),
    application: path.resolve(applicationRoot),
    update: path.resolve(updateRoot),
    vaults: vaultRoots.map((item) => path.resolve(item)),
    secretStores: secretStoreRoots.map((item) => path.resolve(item)),
  };
  assertSeparated(resolved.trace, [
    resolved.application, resolved.update, ...resolved.vaults, ...resolved.secretStores,
  ]);
  const requiredSessions = readRequiredSessions(resolved.manifest);
  const supportedSessions = readSupportedDesktopSessions(
    path.resolve(scenarioCataloguePath), requiredSessions,
  );
  let active = null;

  function authenticate(token) {
    if (!secureTokenMatches(controlToken, token)) {
      throw new BusinessDataDiscoveryControllerError("discovery_control_unauthorised");
    }
  }

  function status({ token } = {}) {
    authenticate(token);
    return {
      enabled: true,
      active: Boolean(active),
      active_session_id: active?.sessionId || null,
      active_scenario: active?.scenario || null,
      surface,
      required_session_count: requiredSessions.size,
      supported_session_count: supportedSessions.size,
      customer_content_included: false,
      raw_paths_included: false,
    };
  }

  function start({ token, sessionId, scenario } = {}) {
    authenticate(token);
    if (active) throw new BusinessDataDiscoveryControllerError("discovery_runtime_session_already_active");
    if (!requiredSessions.has(String(sessionId || ""))) {
      throw new BusinessDataDiscoveryControllerError("discovery_runtime_session_not_required");
    }
    if (!supportedSessions.has(String(sessionId || ""))) {
      throw new BusinessDataDiscoveryControllerError("discovery_runtime_surface_not_required");
    }
    const sessionContract = supportedSessions.get(String(sessionId));
    const tracer = sessionContract.surfaces.has(surface)
      ? createBusinessDataWriteTracer({
          sourceRoot: resolved.source,
          applicationRoot: resolved.application,
          updateRoot: resolved.update,
          vaultRoots: resolved.vaults,
          secretStoreRoots: resolved.secretStores,
          pathFingerprintKey: fingerprintKey,
          maxEvents,
        })
      : null;
    let observedExternalClasses = [];
    if (typeof externalClassProbe === "function") {
      const probed = externalClassProbe({
        sessionId: String(sessionId),
        expectedClasses: [...sessionContract.expectedExternalClasses].sort(),
      });
      if (!Array.isArray(probed) || probed.some((item) => typeof item !== "string" || !item)) {
        throw new BusinessDataDiscoveryControllerError("discovery_external_probe_invalid");
      }
      observedExternalClasses = [...new Set(probed)].sort();
      if (observedExternalClasses.some((item) => !sessionContract.expectedExternalClasses.has(item))) {
        throw new BusinessDataDiscoveryControllerError("discovery_external_probe_unexpected");
      }
    }
    tracer?.start();
    active = {
      tracer,
      sessionId: String(sessionId),
      scenario: String(scenario || sessionId),
      surfaces: sessionContract.surfaces,
      observedExternalClasses,
      rendererEvents: [],
      rendererDropped: 0,
    };
    return status({ token });
  }

  function recordRendererStorage({ operation, storageArea, key } = {}) {
    if (!active || !active.surfaces.has("desktop_renderer")) return false;
    const area = storageArea === "local" ? "local" : storageArea === "session" ? "session" : null;
    const action = ["set", "remove", "clear"].includes(operation) ? operation : null;
    if (!area || !action) return false;
    if (active.rendererEvents.length >= maxEvents) {
      active.rendererDropped += 1;
      return false;
    }
    const identifier = `${area}\0${String(key || "").slice(0, 4096)}`;
    const destinationClass = action === "remove"
      ? "approved_browser_purge"
      : action === "set" && isApprovedRendererPreference(key)
        ? "approved_interface_state"
        : "application_boundary";
    active.rendererEvents.push({
      operation: area === "local" ? "web.local_storage" : "web.session_storage",
      action,
      destination_class: destinationClass,
      destination_hmac_sha256: crypto.createHmac("sha256", fingerprintKey)
        .update(identifier, "utf8")
        .digest("hex"),
      source_path: "desktop/mac/renderer-browser-storage",
      line: 0,
    });
    return true;
  }

  function writeRendererFragment(current, completed) {
    if (!current.surfaces.has("desktop_renderer")) return null;
    const eventCount = current.rendererEvents.length;
    const destinationCounts = {};
    for (const event of current.rendererEvents) {
      destinationCounts[event.destination_class] = (destinationCounts[event.destination_class] || 0) + 1;
    }
    const unsafeWriteCount = current.rendererEvents.filter(
      (event) => event.destination_class === "application_boundary",
    ).length;
    const report = {
      schema_version: "tessaris.business-data-runtime-trace.v1",
      session_id: current.sessionId,
      scenario: current.scenario,
      surface: "desktop_renderer",
      evidence_kind: "browser_storage_observations",
      privacy: "browser_storage_operations_and_keyed_identifier_fingerprints_only_no_raw_keys_or_values",
      observed_vault_domains: [],
      vault_domain_operations: [],
      observed_external_classes: [...current.observedExternalClasses],
      event_count: eventCount,
      scenario_completed: completed,
      dropped_event_count: current.rendererDropped,
      complete: completed && current.rendererDropped === 0,
      destination_counts: Object.fromEntries(Object.entries(destinationCounts).sort()),
      unsafe_write_count: unsafeWriteCount,
      release_gate_passed: completed && current.rendererDropped === 0 && unsafeWriteCount === 0,
      grouped_source_operations: [],
      events: current.rendererEvents.map((event) => ({ ...event })),
    };
    const fragmentPath = path.join(resolved.trace, `${current.sessionId}.desktop_renderer.json`);
    fs.mkdirSync(path.dirname(fragmentPath), { recursive: true, mode: 0o700 });
    fs.writeFileSync(fragmentPath, `${JSON.stringify(report, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
    fs.chmodSync(fragmentPath, 0o600);
    return path.basename(fragmentPath);
  }

  function stop({ token, scenarioCompleted } = {}) {
    authenticate(token);
    if (!active) throw new BusinessDataDiscoveryControllerError("discovery_runtime_session_not_active");
    const completed = scenarioCompleted === true;
    const current = active;
    current.tracer?.stop();
    let report = null;
    let fragmentName = null;
    if (current.surfaces.has(surface)) {
      const fragmentPath = path.join(resolved.trace, `${current.sessionId}.${surface}.json`);
      report = current.tracer.writeReport(fragmentPath, {
        sessionId: current.sessionId,
        scenario: current.scenario,
        scenarioCompleted: completed,
        surface,
      });
      report.observed_external_classes = [...current.observedExternalClasses];
      fs.writeFileSync(fragmentPath, `${JSON.stringify(report, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
      fs.chmodSync(fragmentPath, 0o600);
      fragmentName = path.basename(fragmentPath);
    } else {
      report = {
        session_id: current.sessionId,
        scenario: current.scenario,
        scenario_completed: completed,
        event_count: 0,
        dropped_event_count: 0,
        unsafe_write_count: 0,
      };
    }
    const rendererFragmentName = writeRendererFragment(current, completed);
    active = null;
    const fragmentNames = [fragmentName, rendererFragmentName].filter(Boolean);
    return {
      session_id: report.session_id,
      scenario: report.scenario,
      surfaces: [...current.surfaces].filter((item) => [surface, "desktop_renderer"].includes(item)).sort(),
      scenario_completed: report.scenario_completed,
      event_count: report.event_count + current.rendererEvents.length,
      dropped_event_count: report.dropped_event_count + current.rendererDropped,
      unsafe_write_count: report.unsafe_write_count + current.rendererEvents.filter(
        (event) => event.destination_class === "application_boundary",
      ).length,
      release_gate_passed: completed
        && report.dropped_event_count === 0
        && current.rendererDropped === 0
        && report.unsafe_write_count === 0
        && current.rendererEvents.every(
          (event) => event.destination_class !== "application_boundary",
        )
        && [...supportedSessions.get(current.sessionId).expectedExternalClasses]
          .every((item) => current.observedExternalClasses.includes(item)),
      fragment_name: fragmentName,
      fragment_names: fragmentNames,
      customer_content_included: false,
      raw_paths_included: false,
    };
  }

  return { start, stop, status, recordRendererStorage };
}

module.exports = {
  BusinessDataDiscoveryControllerError,
  createBusinessDataDiscoveryController,
};
