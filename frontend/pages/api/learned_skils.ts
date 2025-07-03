import type { NextApiRequest, NextApiResponse } from 'next';
import fs from "fs";
import path from "path";

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  const filePath = path.resolve("./backend/modules/skills/learned_skills.json");
  try {
    const json = fs.readFileSync(filePath, "utf-8");
    res.status(200).json(JSON.parse(json));
  } catch (err) {
    res.status(500).json({ error: "Failed to load learned skills." });
  }
}