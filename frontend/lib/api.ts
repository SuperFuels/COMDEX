// frontend/lib/api.ts
import axios from 'axios'

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '') ||
  'https://comdex-api-375760843948.us-central1.run.app'

const api = axios.create({
  baseURL: `${BASE_URL}/`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Optional: log all requests to verify you’re hitting the right host
api.interceptors.request.use(req => {
  console.debug('[API] →', req.method?.toUpperCase(), req.baseURL, req.url)
  return req
})

export default api

