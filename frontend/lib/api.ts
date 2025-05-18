// frontend/lib/api.ts
import axios, { AxiosRequestConfig, AxiosError } from 'axios'
import Router from 'next/router'

// Ensure baseURL always ends with a slash
type NullableString = string | undefined
const rawBaseURL: string =
  (process.env.NEXT_PUBLIC_API_URL as string) ||
  'https://comdex-api-375760843948.us-central1.run.app'
const baseURL: string = rawBaseURL.endsWith('/')
  ? rawBaseURL
  : rawBaseURL + '/'

const api = axios.create({
  baseURL,
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  },
  withCredentials: false,
})

// Request interceptor: normalize URL and attach auth token
api.interceptors.request.use(
  (config: AxiosRequestConfig) => {
    // Normalize URL to include trailing slash before query parameters
    if (config.url) {
      const [path, query] = config.url.split('?')
      if (!path.endsWith('/')) {
        config.url = path + '/' + (query ? `?${query}` : '')
      }
    }

    // Attach auth token if present in localStorage
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

// Response interceptor: handle unauthorized
api.interceptors.response.use(
  response => response,
  (error: AxiosError) => {
    const status = error.response?.status
    if ((status === 401 || status === 403) && typeof window !== 'undefined') {
      console.warn(
        '[api] Unauthorized – clearing token and redirecting to /login'
      )
      window.localStorage.removeItem('token')
      Router.replace('/login')
    }
    return Promise.reject(error)
  }
)

export default api

