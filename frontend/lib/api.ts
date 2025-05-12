// frontend/lib/api.ts
import axios, { AxiosRequestConfig, AxiosError } from 'axios'
import Router from 'next/router'

// Create an Axios instance with default settings
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000',
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  },
  // We’re doing stateless Bearer-token auth, so no cookies for now
  withCredentials: false,
})

// ─── Attach JWT from localStorage ───────────────────────────────
api.interceptors.request.use(
  (config: AxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token')
      if (token) {
        config.headers = config.headers ?? {}
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error)
)

// ─── On 401 / 403, clear token and send you back to login ────────
api.interceptors.response.use(
  response => response,
  (error: AxiosError) => {
    const status = error.response?.status
    if ((status === 401 || status === 403) && typeof window !== 'undefined') {
      console.warn('[api] Unauthorized – clearing token and redirecting to /login')
      localStorage.removeItem('token')
      Router.replace('/login')
    }
    return Promise.reject(error)
  }
)

export default api

