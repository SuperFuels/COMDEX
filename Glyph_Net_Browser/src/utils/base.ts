// frontend/src/utils/base.ts
export function resolveApiBase(): string {
  const host = location.host;
  const isCodespaces = host.endsWith(".app.github.dev");
  if (isCodespaces) return `https://${host.replace("-5173", "-8080")}`;
  if (host === "localhost:5173" || host === "127.0.0.1:5173") return "http://localhost:8080";
  const envHost = (import.meta as any)?.env?.VITE_API_HOST as string | undefined;
  if (envHost) {
    const scheme = location.protocol === "https:" ? "https" : "http";
    return `${scheme}://${envHost}`;
  }
  const m = host.match(/^(.*):5173$/);
  if (m) return `${location.protocol}//${m[1]}:8080`;
  return `${location.protocol}//${host}`;
}