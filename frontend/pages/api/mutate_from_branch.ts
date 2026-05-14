// frontend/pages/api/mutate_from_branch.ts
import type { NextApiRequest, NextApiResponse } from "next";

// POST body: { trailId: string }
// Proxies to your Python backend: backend/modules/creative/creative_core.py
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "Method not allowed" });
  }

  const trailId = req.body?.trailId as string | undefined;
  if (!trailId) {
    return res.status(400).json({ error: "Missing required field: trailId" });
  }

  // Where your Python server is running (FastAPI/Flask/etc.)
  const BACKEND_URL =
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    "http://localhost:8000";

  try {
    // Adjust the path to match your Python route that calls retryMutationFromTrail
    // e.g. in FastAPI: POST /creative/retry_mutation_from_trail
    const resp = await fetch(`${BACKEND_URL}/creative/retry_mutation_from_trail`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trail_id: trailId }),
    });

    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      return res.status(resp.status).json({
        error: "backend_error",
        status: resp.status,
        data,
      });
    }

    return res.status(200).json(data);
  } catch (err: any) {
    return res.status(500).json({
      error: "backend_unreachable",
      message: err?.message ?? String(err),
    });
  }
}