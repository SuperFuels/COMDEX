(function installTessarisDesktopBackendOriginRouter(global) {
  "use strict";

  const LEGACY_LOOPBACK = new Set([
    "http://127.0.0.1:8080",
    "http://localhost:8080",
  ]);

  function normalizeLoopbackBase(value) {
    const base = String(value || "").trim().replace(/\/+$/, "");
    if (!/^http:\/\/(?:127\.0\.0\.1|localhost):\d{1,5}$/.test(base)) return "";
    let parsed;
    try {
      parsed = new URL(base);
    } catch (_) {
      return "";
    }
    const port = Number.parseInt(parsed.port, 10);
    return port >= 1 && port <= 65535 ? base : "";
  }

  function rewriteLegacyLoopbackUrl(value, configuredBase) {
    const base = normalizeLoopbackBase(configuredBase);
    if (!base) return value;
    let parsed;
    try {
      parsed = new URL(String(value));
    } catch (_) {
      return value;
    }
    if (!LEGACY_LOOPBACK.has(parsed.origin)) return value;
    return `${base}${parsed.pathname}${parsed.search}${parsed.hash}`;
  }

  function install(target) {
    if (!target || target.__TESSARIS_BACKEND_ORIGIN_ROUTER_INSTALLED__) return;
    const configuredBase = normalizeLoopbackBase(
      target.aionDesktop?.backendApiBase || target.AION_API_BASE,
    );
    if (!configuredBase) return;
    target.__TESSARIS_BACKEND_ORIGIN_ROUTER_INSTALLED__ = true;
    target.AION_API_BASE = configuredBase;
    target.apiBase = configuredBase;

    const originalFetch = typeof target.fetch === "function"
      ? target.fetch.bind(target)
      : null;
    if (originalFetch) {
      target.fetch = function routedDesktopFetch(input, init) {
        if (typeof input === "string" || input instanceof URL) {
          return originalFetch(rewriteLegacyLoopbackUrl(input, configuredBase), init);
        }
        if (typeof target.Request === "function" && input instanceof target.Request) {
          const routed = rewriteLegacyLoopbackUrl(input.url, configuredBase);
          return originalFetch(routed === input.url ? input : new target.Request(routed, input), init);
        }
        return originalFetch(input, init);
      };
    }

    const xhrPrototype = target.XMLHttpRequest?.prototype;
    if (xhrPrototype && typeof xhrPrototype.open === "function") {
      const originalOpen = xhrPrototype.open;
      xhrPrototype.open = function routedDesktopXhrOpen(method, url, ...args) {
        return originalOpen.call(
          this,
          method,
          rewriteLegacyLoopbackUrl(url, configuredBase),
          ...args,
        );
      };
    }
  }

  const api = { install, normalizeLoopbackBase, rewriteLegacyLoopbackUrl };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (global) {
    global.TessarisDesktopBackendOriginRouter = Object.freeze(api);
    install(global);
  }
})(typeof window !== "undefined" ? window : null);
