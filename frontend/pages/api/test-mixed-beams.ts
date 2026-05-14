// File: frontend/pages/api/test-mixed-beams.ts
import fs from "fs";
import path from "path";
import type { NextApiRequest, NextApiResponse } from "next";

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  const filePath = path.resolve(
    process.cwd(),
    "backend/modules/dimensions/containers/tests/mixed_beam_test.dc.json"
  );

  try {
    const data = fs.readFileSync(filePath, "utf-8");
    res.status(200).json(JSON.parse(data));
  } catch (err) {
    res.status(500).json({ error: "Could not load test .dc.json" });
  }
}