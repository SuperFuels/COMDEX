// frontend/src/lib/net.ts
export function backendBase(): string {
  // Works in GitHub Codespaces & local dev
  const { protocol, host } = window.location;
  // vite (5173) → backend (8080)
  const replaced = host.replace("-5173", "-8080");
  return `${protocol}//${replaced}`;
}

export function glyphnetWsUrl(recipient: string, token = "dev-token"): string {
  const isHttps = window.location.protocol === "https:";
  const scheme = isHttps ? "wss" : "ws";
  const host8080 = window.location.host.replace("-5173", "-8080");
  const topic = encodeURIComponent(recipient);
  return `${scheme}://${host8080}/ws/glyphnet?token=${encodeURIComponent(token)}&topic=${topic}`;
}