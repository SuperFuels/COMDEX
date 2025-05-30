import { useState, useEffect } from 'react'
import api from '@/lib/api'

export interface Product {
  id: number
  title: string
  category: string
  origin_country: string
  price_per_kg: number
  image_url: string
}

export interface SupplierDashboardData {
  products: Product[]
  loading: boolean
  error: string | null
}

export default function useSupplierDashboard(): SupplierDashboardData {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchMyProducts = async () => {
      setLoading(true)
      try {
        const token = localStorage.getItem('token')
        if (!token) throw new Error('Not authenticated')

        const res = await api.get<Product[]>('/products/me', {
          headers: { Authorization: `Bearer ${token}` },
          withCredentials: true
        })
        setProducts(res.data)
      } catch (err) {
        console.error('❌ Failed to fetch products', err)
        setError('Unable to load your products.')
      } finally {
        setLoading(false)
      }
    }
    fetchMyProducts()
  }, [])

  return { products, loading, error }
}
