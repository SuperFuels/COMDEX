// API route to handle mutation retry
import type { NextApiRequest, NextApiResponse } from "next";
import { retryMutationFromTrail } from "@/modules/creative_core";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { trailId } = req.body;
  const result = await retryMutationFromTrail(trailId); // returns new glyphs + beams
  res.status(200).json(result);
}