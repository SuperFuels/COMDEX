// frontend/lib/api.ts

import axios from 'axios'

// 🔗 Define base API URL
const BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '') ||
  'https://comdex-api-375760843948.us-central1.run.app'

// 🔧 1) Configure global axios defaults
axios.defaults.baseURL = `${BASE}/`
axios.defaults.headers.common['Content-Type'] = 'application/json'

// ⚙️ 2) Create a custom axios instance
const api = axios.create({
  baseURL: `${BASE}/`,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
})

// 🔐 3) Attach JWT token from localStorage
api.interceptors.request.use((config) => {
  try {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers = config.headers || {}
      config.headers['Authorization'] = `Bearer ${token}`
    }
  } catch (err) {
    console.warn('Token injection failed:', err)
  }
  return config
})

// 🐞 4) Debug all outgoing requests
api.interceptors.request.use((config) => {
  console.debug('[API]', config.method?.toUpperCase(), config.url, config)
  return config
})

export default api
export { axios }

// 🧬 Send glyph mutation request to backend
export async function mutateGlyph(glyph: {
  coord: string
  tag: string
  value: string
  action: string
}) {
  const res = await api.post('/api/aion/mutate-glyph', glyph)
  return res.data
}