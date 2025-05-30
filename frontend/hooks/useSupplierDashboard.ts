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
    async function fetchProducts() {
      setLoading(true)
      try {
        const res = await api.get<Product[]>('/products/me')
        setProducts(res.data)
      } catch (e) {
        console.error('Failed to fetch products', e)
        setError('Unable to load your products.')
      } finally {
        setLoading(false)
      }
    }
    fetchProducts()
  }, [])

  return { products, loading, error }
}
