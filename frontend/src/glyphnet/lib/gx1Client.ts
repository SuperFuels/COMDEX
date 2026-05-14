// Glyph_Net_Browser/src/lib/gx1Client.ts

export type VerifyLine = { text: string; ok: boolean };

export type Gx1InspectResponse = {
  run_id?: string;
  run_dir?: string;
  files?: Record<string, string>;
  index_text?: string;
  sha256_text?: string;

  // Some variants may return these inline
  metrics?: any;
  trace_preview?: any;
  exports?: any;
};

export type Gx1RunResponse = {
  status?: string;
  run_id: string;
  git_rev?: string;
  phase_root?: string;
  run_dir?: string;
  trace_digest?: string;

  metrics?: any;
  trace_preview?: any;
  exports?: any;
  staging_dir?: string;
};

function defaultBase() {
  // Vite dev proxy: leave "" so fetch("/api/gx1/...") hits :5173 and proxies to backend
  return (import.meta as any).env?.VITE_GX1_API_BASE?.replace(/\/+$/, "") || "";
}

export function gx1Url(path: string) {
  const base = defaultBase();
  if (!path.startsWith("/")) path = `/${path}`;
  return `${base}${path}`;
}

export async function gx1Health(): Promise<any> {
  const tryPaths = ["/api/gx1/health", "/health"];
  let lastErr: any = null;

  for (const p of tryPaths) {
    try {
      const res = await fetch(gx1Url(p));
      if (res.ok) return await res.json();
      lastErr = new Error(`Health failed: ${res.status} (${p})`);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error("Health failed");
}

export async function gx1Inspect(runId: string): Promise<Gx1InspectResponse> {
  const res = await fetch(gx1Url(`/api/gx1/runs/${encodeURIComponent(runId)}`));
  if (!res.ok) throw new Error(`Inspect failed: ${res.status}`);
  return await res.json();
}

export async function gx1FetchRunFile(runId: string, rel: string) {
  const res = await fetch(
    gx1Url(`/api/gx1/runs/${encodeURIComponent(runId)}/file?rel=${encodeURIComponent(rel)}`),
  );
  if (!res.ok) throw new Error(`File fetch failed (${rel}): ${res.status}`);
  return res;
}

/**
 * Matches backend.gx1_api_min:
 * POST /api/gx1/run
 * multipart:
 *   - manifest: file (application/json)
 *   - dataset: file  (text/plain or application/jsonl)
 */
export async function gx1Run(params: {
  manifestJson: any;
  datasetFile: File;
  manifestFilename?: string;
}) {
  const form = new FormData();

  const manifestText = JSON.stringify(params.manifestJson, null, 2);
  const manifestBlob = new Blob([manifestText], { type: "application/json" });
  const manifestName = params.manifestFilename || "gx1_manifest.json";

  form.set("manifest", manifestBlob, manifestName);
  form.set("dataset", params.datasetFile);

  const res = await fetch(gx1Url("/api/gx1/run"), { method: "POST", body: form });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`GX1 run failed: ${res.status}\n${txt}`);
  }
  return (await res.json()) as Gx1RunResponse;
}

/* =========================
   Download helpers
   ========================= */

export async function gx1DownloadRunFile(runId: string, rel: string, suggestedName?: string) {
  const res = await gx1FetchRunFile(runId, rel);
  const blob = await res.blob();

  const a = document.createElement("a");
  const url = URL.createObjectURL(blob);
  a.href = url;
  a.download = suggestedName || rel;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function gx1DownloadAllArtifacts(runId: string, files: Record<string, string>) {
  // Sequential downloads to avoid browser blocking popups; still user-initiated by one click.
  const names = Object.keys(files || {});
  for (const rel of names) {
    try {
      await gx1DownloadRunFile(runId, rel);
      // tiny yield so UI remains responsive
      await new Promise((r) => setTimeout(r, 50));
    } catch (e) {
      console.warn("Download failed:", rel, e);
    }
  }
}

/* =========================
   Verify (client-side)
   ========================= */

function parseSha256Text(sha256Text: string): Array<{ file: string; sha256: string }> {
  const out: Array<{ file: string; sha256: string }> = [];
  const lines = (sha256Text || "")
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);

  for (const line of lines) {
    // supports: "<hash>  <file>" or "<hash> <file>"
    const m = line.match(/^([a-fA-F0-9]{64})\s+(.+?)\s*$/);
    if (!m) continue;
    out.push({ sha256: m[1].toLowerCase(), file: m[2].trim() });
  }
  return out;
}

async function sha256Hex(buf: ArrayBuffer): Promise<string> {
  const hash = await crypto.subtle.digest("SHA-256", buf);
  const bytes = new Uint8Array(hash);
  let hex = "";
  for (const b of bytes) hex += b.toString(16).padStart(2, "0");
  return hex;
}

export async function gx1Verify(runId: string): Promise<{
  runChecks: VerifyLine[];
  indexChecks: VerifyLine[];
}> {
  const info: any = await gx1Inspect(runId);
  const rid = info.run_id || runId;

  const shaText: string = info.sha256_text || info.sha256Text || "";
  const idxText: string = info.index_text || info.indexText || "";

  if (!shaText.trim()) {
    return {
      runChecks: [{ text: "ARTIFACTS.sha256 missing in backend response (sha256_text empty).", ok: false }],
      indexChecks: [{ text: "Cannot verify ARTIFACTS_INDEX.md without sha256 list.", ok: false }],
    };
  }

  const entries = parseSha256Text(shaText);
  if (!entries.length) {
    return {
      runChecks: [{ text: "Failed to parse ARTIFACTS.sha256 (no entries found).", ok: false }],
      indexChecks: [{ text: "Check ARTIFACTS.sha256 formatting.", ok: false }],
    };
  }

  const runChecks: VerifyLine[] = [];
  for (const { file, sha256 } of entries) {
    try {
      const res = await gx1FetchRunFile(rid, file);
      const buf = await res.arrayBuffer();
      const got = await sha256Hex(buf);
      const ok = got === sha256;
      runChecks.push({
        text: `${ok ? "OK" : "FAIL"}  ${file}\n  expected=${sha256}\n  got     =${got}`,
        ok,
      });
    } catch (e: any) {
      runChecks.push({ text: `FAIL ${file}\n  fetch/hash error: ${String(e?.message || e)}`, ok: false });
    }
  }

  const indexChecks: VerifyLine[] = [];
  if (!idxText.trim()) {
    indexChecks.push({ text: "WARN ARTIFACTS_INDEX.md text not returned (index_text empty).", ok: false });
  } else {
    const mentioned = entries.filter((e) => idxText.includes(e.file)).length;
    const ok = mentioned >= Math.max(1, entries.length - 2); // tolerate minor formatting variance
    indexChecks.push({
      text: `${ok ? "OK" : "WARN"} ARTIFACTS_INDEX.md references ${mentioned}/${entries.length} files from ARTIFACTS.sha256`,
      ok,
    });
    const hasRunDir = /run_dir:/i.test(idxText);
    indexChecks.push({ text: `${hasRunDir ? "OK" : "WARN"} ARTIFACTS_INDEX.md contains run_dir header`, ok: hasRunDir });
  }

  return { runChecks, indexChecks };
}