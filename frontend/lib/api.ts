// frontend/lib/api.ts
import axios, { AxiosRequestConfig, AxiosError } from 'axios'
import Router from 'next/router'

// 1️⃣ Require that NEXT_PUBLIC_API_URL is set (and must be HTTPS)
if (!process.env.NEXT_PUBLIC_API_URL) {
  throw new Error(
    'Missing env var NEXT_PUBLIC_API_URL — please set it to your Cloud Run URL'
  )
}
const rawBaseURL = process.env.NEXT_PUBLIC_API_URL
if (!rawBaseURL.startsWith('https://')) {
  throw new Error(
    `NEXT_PUBLIC_API_URL must start with "https://", but got "${rawBaseURL}"`
  )
}

// 2️⃣ Ensure baseURL always ends with a slash
const baseURL = rawBaseURL.endsWith('/') ? rawBaseURL : rawBaseURL + '/'

const api = axios.create({
  baseURL,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  },
  withCredentials: false, // adjust if you ever need cookies
})

// 3️⃣ Normalize every request URL and attach auth token
api.interceptors.request.use(
  (config: AxiosRequestConfig) => {
    if (config.url) {
      const [path, qs] = config.url.split('?')
      if (!path.endsWith('/')) {
        config.url = path + '/' + (qs ? `?${qs}` : '')
      }
    }

    if (typeof window !== 'undefined') {
      const token = window.localStorage.getItem('token')
      if (token) {
        config.headers = config.headers || {}
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error)
)

// 4️⃣ Global 401/403 handler
api.interceptors.response.use(
  response => response,
  (error: AxiosError) => {
    const status = error.response?.status
    if ((status === 401 || status === 403) && typeof window !== 'undefined') {
      console.warn('[api] Unauthorized – clearing token and redirecting to /login')
      window.localStorage.removeItem('token')
      Router.replace('/login')
    }
    return Promise.reject(error)
  }
)

export default api

