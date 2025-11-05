// Picks correct backend endpoints for Codespaces vs local dev.
export function backendEndpoints() {
  const host = location.host;
  const isCodespaces = host.endsWith(".app.github.dev");

  if (isCodespaces) {
    const h8080 = host.replace("-5173", "-8080");
    return {
      http: `https://${h8080}`,
      ws:   `wss://${h8080}`,
    };
  }

  // Local dev: honor current page scheme
  const apiHost = import.meta.env.VITE_API_HOST || "localhost:8080";
  const http = `${location.protocol === "https:" ? "https" : "http"}://${apiHost}`;
  const ws   = `${location.protocol === "https:" ? "wss"   : "ws"}://${apiHost}`;
  return { http, ws };
}