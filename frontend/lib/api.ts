// frontend/lib/api.ts

import axios from 'axios'

// 🔗 Define base API URL
const BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '') ||
  'https://comdex-api-375760843948.us-central1.run.app'

// 🔧 1) Configure global axios defaults
axios.defaults.baseURL = `${BASE}/`
axios.defaults.headers.common['Content-Type'] = 'application/json'

// ⚙️ 2) Create custom axios instance
const api = axios.create({
  baseURL: `${BASE}/`,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
})

// Browser authentication is carried by the backend-issued HttpOnly session
// cookie. Do not copy credentials into script-readable browser storage or
// request logs.

export default api
export { axios }

// 🧠 AION scoring + mutation
export async function scoreMutation(glyph: {
  coord: string
  tag: string
  value: string
  action: string
}) {
  const res = await api.post('/aion/score-mutation', { glyph })
  return res.data
}

export async function mutateGlyph(glyph: {
  coord: string
  tag: string
  value: string
  action: string
}) {
  const res = await api.post('/aion/mutate-glyph', glyph)
  return res.data
}

// ⚙️ Codex execution endpoints
export async function runCodexScroll(scroll: string, context: Record<string, any> = {}) {
  const res = await api.post('/codex/scroll', { scroll, context })
  return res.data
}

export async function runPhotonCapsule(capsule: Record<string, any> | string) {
  const res = await api.post('/codex/run-photon', { capsule })
  return res.data
}

export async function runPhotonPage(content: Record<string, any> | string) {
  const res = await api.post('/codex/run-ptn', { content })
  return res.data
}

// ─────────────────────────────────────
// 🎞️ Replay System (NEW)
// ─────────────────────────────────────
export async function applyReplay(frames: any[]) {
  const res = await api.post('/replay/apply', { frames })

  if (res.status !== 200) {
    throw new Error('Replay apply failed')
  }

  return res.data
}
