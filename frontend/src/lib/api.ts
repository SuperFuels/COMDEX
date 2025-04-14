// src/lib/api.ts
import axios from 'axios'

const API_BASE = 'http://127.0.0.1:8000'

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
})

// ✅ GET: Fetch all products
export async function getProducts() {
  const token = localStorage.getItem('token')

  if (!token) {
    throw new Error('Not authenticated')
  }

  const res = await api.get('/products/', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  return res.data
}

// ✅ POST: Create new product
export async function createProduct(data: any, token: string) {
  const res = await api.post('/products/create', data, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
  return res.data
}

// ✅ POST: Register user
export async function registerUser(userData: any) {
  const res = await api.post('/auth/register', userData)
  return res.data
}

// ✅ POST: Login user
export async function loginUser(userData: any) {
  const res = await api.post('/auth/login', userData)
  return res.data
}

export default api

