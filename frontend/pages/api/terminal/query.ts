// File: frontend/pages/api/terminal/query.ts

import type { NextApiRequest, NextApiResponse } from 'next'
import api from '@/lib/api'           // your existing Axios instance for /products, etc.
import { OpenAI } from 'openai'       // OpenAI Node.js SDK (v4+)

type ProductRecord = {
  id: number
  title: string
  description: string
  price_per_kg: number
  origin_country: string
  image_url: string
  // any other fields your database returns
}

type ChartPoint = {
  time: number
  value: number
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<{
    analysisText: string
    visualPayload:
      | { products?: ProductRecord[]; nextPage?: number }
      | { chartData?: ChartPoint[] }
  }>
) {
  // Only allow POST
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST')
    return res.status(405).json({ analysisText: '', visualPayload: {} })
  }

  // Extract prompt (and optional page) from request body
  const { prompt, page: rawPage } = req.body as { prompt: string; page?: number }
  if (!prompt || typeof prompt !== 'string') {
    return res.status(400).json({ analysisText: '', visualPayload: {} })
  }

  // Default to page 1 if none provided
  const page = typeof rawPage === 'number' ? rawPage : 1
  const lower = prompt.toLowerCase()

  // Heuristic for “product search” prompts
  const isLikelyProductSearch =
    lower.includes('supplier') ||
    lower.includes('whey') ||
    lower.includes('protein') ||
    / in [A-Za-z]+/.test(lower)

  // ─── CASE A: PRODUCT SEARCH ───────────────────────────────────────────────
  if (isLikelyProductSearch) {
    let products: ProductRecord[] = []
    let nextPage: number | undefined = undefined

    try {
      // Call existing /products endpoint: limit=10, current page
      const resp = await api.get<ProductRecord[]>(
        `/products?search=${encodeURIComponent(prompt)}&limit=10&page=${page}`
      )
      products = resp.data || []
      // If we got exactly 10 results, assume there’s another page
      if (products.length === 10) {
        nextPage = page + 1
      }
    } catch (err) {
      console.error('Product search failed', err)
      products = []
    }

    const analysisText = `I performed a search for "${prompt}" and found ${products.length} result(s).`
    return res.status(200).json({
      analysisText,
      visualPayload: { products, nextPage },
    })
  }

  // ─── CASE B: LLM ANALYSIS / CHART ───────────────────────────────────────────
  const systemPrompt = `
You are Stickey.ai’s “Central Command” assistant. When a user asks a question, you must return EXACTLY one JSON object with keys:
  • "analysisText": string (for the left pane)
  • optionally "chartData": array of { "time": UNIX_TIMESTAMP, "value": NUMBER } (for a chart on the right pane)

If the user’s request implies a time-series (e.g. "Build my sales report" or "price trend"), return both keys. If it’s purely textual, return only { "analysisText": ... }. Do NOT output anything else—no markdown fences, no extra keys.
  `.trim()

  const userPrompt = prompt.trim()
  let llmContent = ''

  try {
    const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY })
    const chatResp = await openai.chat.completions.create({
      model: 'gpt-4',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user',   content: userPrompt },
      ],
      temperature: 0.7,
      max_tokens: 400,
    })
    llmContent = chatResp.choices[0].message?.content || ''
  } catch (err) {
    console.error('LLM error:', err)
    llmContent = JSON.stringify({
      analysisText: '❌ I’m sorry, I could not generate a response right now.',
    })
  }

  // Attempt to parse JSON from the model’s reply
  let parsed: { analysisText?: string; chartData?: ChartPoint[] } = {}
  try {
    parsed = JSON.parse(llmContent)
  } catch {
    parsed = { analysisText: llmContent }
  }

  return res.status(200).json({
    analysisText: parsed.analysisText || llmContent,
    visualPayload: { chartData: parsed.chartData },
  })
}