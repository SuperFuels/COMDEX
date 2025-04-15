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

// ✅ DELETE: Delete product by ID
export async function deleteProduct(id: number) {
  const token = localStorage.getItem('token')

  if (!token) {
    throw new Error('Not authenticated')
  }

  const res = await api.delete(`/products/${id}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  return res.data
}

// ✅ POST: Register user
export async function registerUser(userData: { name: string; email: string; password: string }) {
  const res = await api.post('/auth/register', {
    name: userData.name,
    email: userData.email,
    password: userData.password,
  })
  return res.data
}

// ✅ POST: Login user
export async function loginUser(userData: { email: string; password: string }) {
  const res = await api.post('/auth/login', {
    email: userData.email,
    password: userData.password,
  })
  return res.data
}

// ✅ PUT: Update product
export async function updateProduct(productId: number, data: any, token: string) {
  const res = await api.put(`/products/edit/${productId}`, data, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
  return res.data
}

export default api

// ✅ GET: Download deal PDF
export async function downloadDealPdf(dealId: number, token: string) {
  const res = await api.get(`/deals/pdf/${dealId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    responseType: 'blob', // Important for binary data
  })

  // Trigger download in browser
  const url = window.URL.createObjectURL(new Blob([res.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `deal_${dealId}.pdf`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// ✅ POST: Create a new deal
export async function createDeal(dealData: any) {
  const token = localStorage.getItem("token");

  if (!token) {
    throw new Error("Not authenticated");
  }

  const res = await api.post("/deals/create", dealData, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return res.data;
}

