export type InjectPayload = {
  container_path: string;
  lean_path: string;
  overwrite?: boolean;
  auto_clean?: boolean;
  dedupe?: boolean;
  preview?: "raw" | "normalized";
  validate?: boolean;
  diff?: boolean;
  pretty?: boolean;
  ascii?: boolean;
  mermaid_out?: string | null;
  png_out?: string | null;
  report?: "md" | "json" | null;
  report_out?: string | null;
  dot?: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function injectLean(payload: InjectPayload) {
  const res = await fetch(`${API_BASE}/api/lean/inject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Inject failed: ${await res.text()}`);
  return res.json();
}

export async function exportLean(lean_path: string, container_type = "dc", out?: string) {
  const res = await fetch(`${API_BASE}/api/lean/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lean_path, container_type, out }),
  });
  if (!res.ok) throw new Error(`Export failed: ${await res.text()}`);
  return res.json();
}