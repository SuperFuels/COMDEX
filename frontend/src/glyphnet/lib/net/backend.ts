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
  const apiHost =
    (process.env.NEXT_PUBLIC_GLYPHNET_HTTP_BASE ?? "http://localhost:8080")
      .replace(/^https?:\/\//, "");
  const http = `${location.protocol === "https:" ? "https" : "http"}://${apiHost}`;
  const ws   = `${location.protocol === "https:" ? "wss"   : "ws"}://${apiHost}`;
  return { http, ws };
}