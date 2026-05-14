// server/src/index.ts
import express, { Request, Response, NextFunction } from "express";
import kgApp from "./kg"; // default export from kg.ts

const app = express();

// Parse JSON once up front (kgApp also parses; double-parse is harmless)
app.use(express.json({ limit: "10mb", strict: true }));

// --- Optional: lightweight pre-normalizer for visit events ------------------
// (kg.ts already computes host/href using Referer/Origin; this is just a no-op
// helper that fills host if missing without touching kg.ts.)
function normalizeVisitEvent(it: any) {
  if (!it || typeof it !== "object" || it.type !== "visit") return it;
  const p: any = (it as any).payload || {};
  if (!p.host) {
    try {
      const href = p.href || p.uri || "";
      const u = href && /^https?:\/\//i.test(href)
        ? new URL(href)
        : new URL(href || "/", "https://x.invalid");
      p.host = u.host || "";
    } catch {
      p.host = "";
    }
  }
  (it as any).payload = p;
  return it;
}

// Simple health probes
app.get("/", (_req, res) => res.type("text/plain").send("OK"));
app.get("/api/_health", (_req, res) => res.json({ ok: true, where: "index.ts" }));

// Mount the KG routes (they already include /api/... in their paths)
app.use(kgApp);

// JSON 404 for anything unmatched
app.use((req, res) => {
  res.status(404).json({ ok: false, error: "not_found", path: req.path });
});

// Central JSON error handler (helps avoid HTML error pages)
app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
  console.error("[server] unhandled error", err);
  res.status(500).json({ ok: false, error: "server_error" });
});

const PORT = Number(process.env.PORT || 3000);
app.listen(PORT, () => {
  console.log(`[server] listening on http://localhost:${PORT}`);
});

export default app;