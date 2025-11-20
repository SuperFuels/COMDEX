import express from "express";
import kgApp from "./kg";

const app = express();

// Parse JSON so we can normalize before handing off
app.use(express.json({ limit: "10mb" }));

// --- Normalize visit events before KG routes ---
function normalizeVisitEvent(it: any) {
  if (!it || it.type !== "visit") return it;
  const p: any = it.payload || {};
  if (!p.host) {
    try {
      const href = p.href || p.uri || "";
      const u = href && /^https?:/i.test(href)
        ? new URL(href)
        : new URL(href || "/", "https://x.invalid");
      p.host = u.host || "";
    } catch {
      p.host = "";
    }
  }
  it.payload = p;
  return it;
}

// Pre-process bodies for both "events" and "items" shapes
app.use(["/api/kg/events", "/api/kg/append"], (req, _res, next) => {
  try {
    if (Array.isArray((req as any).body?.events)) {
      (req as any).body.events = (req as any).body.events.map(normalizeVisitEvent);
    } else if (Array.isArray((req as any).body?.items)) {
      (req as any).body.items = (req as any).body.items.map(normalizeVisitEvent);
    }
  } catch {}
  next();
});

app.get("/", (_req, res) => res.type("text/plain").send("OK")); // quick health check

// Mount the KG routes: /api/kg/events and /api/kg/query
app.use(kgApp);

const PORT = Number(process.env.PORT || 3000); // ← keep 3000 by default
app.listen(PORT, () => {
  console.log(`[server] listening on http://localhost:${PORT}`);
});