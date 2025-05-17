// frontend/lib/api.ts
import axios, { AxiosRequestConfig, AxiosError } from 'axios'
import Router from 'next/router'

const api = axios.create({
  baseURL:
    process.env.NEXT_PUBLIC_API_URL ??
    'https://comdex-api-375760843948.us-central1.run.app',
  headers: {
    Accept: 'application/json',
    'Content-Type': 'application/json',
  },
  withCredentials: false,
})

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

api.interceptors.response.use(
  response => response,
  (error: AxiosError) => {
    const status = error.response?.status
    if ((status === 401 || status === 403) && typeof window !== 'undefined') {
      console.warn(
        '[api] Unauthorized – clearing token and redirecting to /login'
      )
      localStorage.removeItem('token')
      Router.replace('/login')
    }
    return Promise.reject(error)
  }
)

export default api

