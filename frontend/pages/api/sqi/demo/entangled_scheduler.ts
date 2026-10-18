import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ detail: "Method not allowed" });
  }

  const backend = (process.env.SQI_BACKEND_URL || "").replace(/\/$/, "");
  if (!backend) {
    return res
      .status(503)
      .json({ detail: "SQI_BACKEND_URL is not set (no backend to call)." });
  }

  const url = `${backend}/api/sqi/demo/entangled_scheduler`;

  try {
    const upstream = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req.body ?? {}),
      cache: "no-store",
    });

    const text = await upstream.text();

    res.status(upstream.status);
    res.setHeader(
      "content-type",
      upstream.headers.get("content-type") || "application/json",
    );
    return res.send(text);
  } catch (error) {
    return res.status(502).json({
      detail:
        error instanceof Error
          ? error.message
          : "Failed to reach SQI backend",
    });
  }
}