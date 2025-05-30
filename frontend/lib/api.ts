// frontend/lib/api.ts
import axios from 'axios'

const BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '') ||
  'https://comdex-api-375760843948.us-central1.run.app'

// 1) Configure global axios defaults for any raw axios calls
axios.defaults.baseURL = `${BASE}/`
axios.defaults.headers.common['Content-Type'] = 'application/json'

// 2) Create a dedicated instance for your app
const api = axios.create({
  baseURL: `${BASE}/`,
  withCredentials: true,          // send HTTP-only cookies if your backend sets them
  headers: {
    'Content-Type': 'application/json',
  },
})

// 3) Automatically inject the JWT from localStorage into every request
api.interceptors.request.use((config) => {
  try {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers = config.headers || {}
      config.headers['Authorization'] = `Bearer ${token}`
    }
  } catch {
    // localStorage may be unavailable during SSR
  }
  return config
})

// 4) (Optional) Log every request for easier debugging
api.interceptors.request.use((config) => {
  console.debug('[API] →', config.method?.toUpperCase(), config.baseURL, config.url)
  return config
})

export default api
export { axios }