// File: frontend/pages/api/terminal/query.ts

import type { NextApiRequest, NextApiResponse } from 'next';
import { OpenAI } from 'openai';

type ProductRecord = {
  id: number;
  title: string;
  description: string;
  price_per_kg: number;
  origin_country: string;
  image_url: string;
  // any other fields your backend returns
};

type ChartPoint = {
  time: number;
  value: number;
};

type ResponsePayload = {
  analysisText: string;
  visualPayload:
    | { products?: ProductRecord[]; nextPage?: number }
    | { chartData?: ChartPoint[] };
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ResponsePayload>
) {
  // ─── 1) Only allow POST ───────────────────────────────────────────────
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({
      analysisText: '',
      visualPayload: {},
    });
  }

  // ─── 2) Pull out "prompt" and optional "page" from the JSON body ──────
  const { prompt, page: rawPage } = req.body as { prompt: string; page?: number };
  if (!prompt || typeof prompt !== 'string') {
    return res.status(400).json({
      analysisText: '',
      visualPayload: {},
    });
  }

  const page = typeof rawPage === 'number' ? rawPage : 1;
  const lower = prompt.toLowerCase();

  // ─── 3) Decide if this is a "product search" prompt ─────────────────
  const isLikelyProductSearch =
    lower.includes('supplier') ||
    lower.includes('whey') ||
    lower.includes('protein') ||
    / in [A-Za-z]+/.test(lower);

  // Your Cloud Run (or other remote) base URL:
  const BASE_API = process.env.NEXT_PUBLIC_API_URL;
  if (!BASE_API) {
    console.error('❌ NEXT_PUBLIC_API_URL is not defined');
    return res.status(500).json({
      analysisText: 'Internal server error (missing NEXT_PUBLIC_API_URL)',
      visualPayload: {},
    });
  }

  // ─── CASE A: PRODUCT SEARCH ───────────────────────────────────────────
  if (isLikelyProductSearch) {
    let products: ProductRecord[] = [];
    let nextPage: number | undefined = undefined;

    try {
      // Build the remote URL to fetch /products?search=…&limit=10&page=…
      const url = `${BASE_API}/products?search=${encodeURIComponent(
        prompt
      )}&limit=10&page=${page}`;

      // You can use `fetch` directly, since Next.js API routes run on Node 18+:
      const backendRes = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!backendRes.ok) {
        console.error('🔴 Remote /products returned status', backendRes.status);
        products = [];
      } else {
        products = (await backendRes.json()) as ProductRecord[];
      }

      if (products.length === 10) {
        // assume there might be a “page + 1”
        nextPage = page + 1;
      }
    } catch (fetchErr) {
      console.error('🔴 Product search failed:', fetchErr);
      products = [];
    }

    const analysisText = `I performed a search for “${prompt}” and found ${products.length} result(s).`;
    return res.status(200).json({
      analysisText,
      visualPayload: { products, nextPage },
    });
  }

  // ─── CASE B: LLM ANALYSIS / CHART ─────────────────────────────────────
  const systemPrompt = `
You are Stickey.ai’s “Central Command” assistant. Return EXACTLY one JSON object with:
  • "analysisText": string
  • optionally "chartData": array of { "time": UNIX_TIMESTAMP, "value": NUMBER }
If the user’s request suggests a time-series, return both keys. Otherwise return only { "analysisText": ... }.
Do NOT output anything else.
  `.trim();

  const userPrompt = prompt.trim();
  let llmContent = '';

  try {
    // Instantiate the OpenAI SDK
    const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY! });
    const chatResp = await openai.chat.completions.create({
      model: 'gpt-4',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      temperature: 0.7,
      max_tokens: 400,
    });

    llmContent = chatResp.choices[0].message?.content || '';
  } catch (err) {
    console.error('🔴 LLM error:', err);
    llmContent = JSON.stringify({
      analysisText: '❌ I’m sorry, I could not generate a response right now.',
    });
  }

  // Attempt to parse JSON from the LLM’s reply
  let parsed: { analysisText?: string; chartData?: ChartPoint[] } = {};
  try {
    parsed = JSON.parse(llmContent);
  } catch (parseErr) {
    parsed = { analysisText: llmContent };
  }

  return res.status(200).json({
    analysisText: parsed.analysisText || llmContent,
    visualPayload: { chartData: parsed.chartData },
  });
}