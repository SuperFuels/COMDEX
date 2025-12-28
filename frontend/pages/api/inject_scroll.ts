// frontend/pages/api/inject_scroll.ts
// ✅ Inject a scroll into the QFC or GHX field
// Triggered by drop events, symbolic field actions, or UI triggers

import type { NextApiRequest, NextApiResponse } from "next";

// Optional: Log or broadcast via GHX
// import { sendGHXInjection } from "@/utils/ws/ghx_broadcast";

const API_BASE =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.BACKEND_URL ||
  "http://127.0.0.1:8080";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    res.setHeader("Allow", ["POST"]);
    return res.status(405).json({ error: "Method Not Allowed" });
  }

  try {
    const { scrollId, glyph, target = "qfc" } = (req.body ?? {}) as {
      scrollId?: string;
      glyph?: any;
      target?: string;
    };

    if (!scrollId) return res.status(400).json({ error: "Missing scrollId" });
    if (glyph === undefined || glyph === null)
      return res.status(400).json({ error: "Missing glyph" });

    const backendRes = await fetch(`${API_BASE}/api/inject_scroll`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scrollId, glyph, target }),
    });

    const raw = await backendRes.text();
    let result: any = raw;
    try {
      result = raw ? JSON.parse(raw) : null;
    } catch {
      // keep as text
    }

    if (!backendRes.ok) {
      return res.status(backendRes.status).json({
        error: "Backend error",
        status: backendRes.status,
        result,
      });
    }

    // sendGHXInjection({ type: "scroll_injected", scrollId, glyph, target });

    return res.status(200).json({ status: "ok", result });
  } catch (err: any) {
    console.error("Error injecting scroll:", err);
    return res.status(500).json({
      error: "Injection failed",
      details: err?.message || String(err),
    });
  }
}