// frontend/utils/api.ts
import axios from 'axios'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,  // ← use your env var
  // any other defaults (timeout, headers, etc)…
})

export default api

