import express from "express";
import kgApp from "./kg";

const app = express();

app.get("/", (_req, res) => res.type("text/plain").send("OK")); // quick health check

// Mount the KG routes: /api/kg/events and /api/kg/query
app.use(kgApp);

const PORT = Number(process.env.PORT || 3000); // ← keep 3000 by default
app.listen(PORT, () => {
  console.log(`[server] listening on http://localhost:${PORT}`);
});