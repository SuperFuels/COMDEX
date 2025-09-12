// ✅ Inject a scroll into the QFC or GHX field
// Triggered by drop events, symbolic field actions, or UI triggers

import type { NextApiRequest, NextApiResponse } from "next";

// Optional: Log or broadcast via GHX
// import { sendGHXInjection } from "@/utils/ws/ghx_broadcast";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method Not Allowed" });
  }

  try {
    const { scrollId, glyph, target = "qfc" } = req.body;

    // ✅ Forward to Python API backend
    const backendRes = await fetch("http://localhost:8000/api/inject_scroll", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scrollId, glyph, target }),
    });

    const result = await backendRes.json();

    // ✅ Optionally broadcast to GHX HUD (if not done server-side)
    // sendGHXInjection({ type: "scroll_injected", scrollId, glyph, target });

    return res.status(200).json({ status: "ok", result });
  } catch (err) {
    console.error("Error injecting scroll:", err);
    return res.status(500).json({ error: "Injection failed" });
  }
}