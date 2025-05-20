// frontend/lib/api.ts
import axios from 'axios'

const BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '') ||
  'https://comdex-api-375760843948.us-central1.run.app'

// 1) Override global axios defaults so any raw `axios.get('/foo')`
//    uses your Cloud Run URL.
axios.defaults.baseURL = `${BASE}/`
axios.defaults.headers.common['Content-Type'] = 'application/json'

// 2) Create your own axios instance for explicit use & interceptors
const api = axios.create({
  baseURL: `${BASE}/`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 3) (Optional) Log every request to confirm it’s going to the right place
api.interceptors.request.use(req => {
  console.debug('[API] →', req.method?.toUpperCase(), req.baseURL, req.url)
  return req
})

export default api
export { axios }

