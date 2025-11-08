// frontend/src/lib/net.ts

/**
 * Resolve the backend host for different environments:
 * - GitHub Codespaces:  ...-5173.app.github.dev  ->  ...-8080.app.github.dev
 * - Local Vite dev:     localhost:5173           ->  localhost:8080
 *                       127.0.0.1:5173           ->  127.0.0.1:8080
 * - Prod/other:         keep host as-is
 */
function resolveBackendHost(): string {
  const { host, hostname } = window.location;

  // Codespaces pattern: "-5173.app.github.dev" → "-8080.app.github.dev"
  if (host.endsWith(".app.github.dev")) {
    return host.replace("-5173", "-8080");
  }

  // Local vite dev ports → backend on 8080
  if (host.endsWith(":5173")) {
    return `${hostname}:8080`;
  }

  // Default: same host
  return host;
}

export function backendBase(): string {
  const proto = window.location.protocol; // "http:" | "https:"
  return `${proto}//${resolveBackendHost()}`;
}

export function glyphnetWsUrl(recipient: string, token = "dev-token"): string {
  const isHttps = window.location.protocol === "https:";
  const scheme = isHttps ? "wss" : "ws";
  const host = resolveBackendHost();

  const qs = new URLSearchParams({
    token,
    topic: recipient, // raw ucs://... value; URLSearchParams will encode
  });

  return `${scheme}://${host}/ws/glyphnet?${qs.toString()}`;
}