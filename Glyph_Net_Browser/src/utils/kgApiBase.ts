// src/utils/kgApiBase.ts
export const KG_API_BASE: string = (() => {
  const raw = (import.meta as any).env?.VITE_KG_URL as string | undefined;
  const env = (raw || "").trim().replace(/\/$/, "");

  // Only honor explicit URL when we're really on localhost/127.*
  if (env && /^https?:\/\//i.test(env)) {
    if (typeof window !== "undefined") {
      const h = window.location.hostname;
      const onLocalHost = h === "localhost" || h.startsWith("127.");
      if (onLocalHost) return env;     // direct call OK in local dev
      // In Codespaces or any remote host → use proxy
      return "";
    }
    // SSR/build-time: be conservative; client will still use proxy
    return "";
  }

  // Default: same-origin → Vite proxy handles /api/kg/*
  return "";
})();