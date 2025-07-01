import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") return res.status(405).end("Method not allowed");

  const { prompt } = req.body;

  try {
    const backendRes = await fetch(
      "https://comdex-api-375760843948.us-central1.run.app/api/aion/prompt",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      }
    );

    const data = await backendRes.json();

    if (!backendRes.ok) {
      return res.status(500).json({ reply: "❌ AION error: " + data.detail });
    }

    res.status(200).json({ reply: data.reply });
  } catch (err) {
    res.status(500).json({ reply: "❌ AION backend unreachable." });
  }
}
