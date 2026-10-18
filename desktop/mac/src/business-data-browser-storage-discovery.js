(() => {
  "use strict";

  const desktop = window.aionDesktop;
  if (!desktop?.businessDataDiscoveryEnabled || typeof window.Storage === "undefined") return;
  const prototype = window.Storage.prototype;
  if (prototype.__tessarisBusinessDataDiscoveryInstalled === true) return;
  Object.defineProperty(prototype, "__tessarisBusinessDataDiscoveryInstalled", {
    value: true,
    configurable: false,
    enumerable: false,
    writable: false,
  });

  for (const [method, operation] of [["setItem", "set"], ["removeItem", "remove"], ["clear", "clear"]]) {
    const original = prototype[method];
    if (typeof original !== "function") continue;
    Object.defineProperty(prototype, method, {
      configurable: true,
      enumerable: false,
      writable: true,
      value: function tracedBrowserStorageWrite(...args) {
        const result = original.apply(this, args);
        let storageArea = "unknown";
        try {
          if (this === window.localStorage) storageArea = "local";
          else if (this === window.sessionStorage) storageArea = "session";
        } catch {}
        desktop.recordBusinessDataBrowserWrite({
          operation,
          storageArea,
          key: operation === "clear" ? "*" : String(args[0] || ""),
        });
        return result;
      },
    });
  }
})();
