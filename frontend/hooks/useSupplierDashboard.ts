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
  totalSalesToday: number
  activeListings: number
  stock: number
  capacity: number
  openOrders: number
  proceeds30d: number
  feedbackRating: number
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
          headers: { Authorization: `Bearer ${token}` }
        })
        setProducts(res.data)
      } catch (err) {
        console.error('❌ Failed to fetch products', err)
        setError('Failed to load dashboard data.')
      } finally {
        setLoading(false)
      }
    }
    fetchMyProducts()
  }, [])

  // Stub metrics for now
  const totalSalesToday = 0
  const activeListings    = products.length
  const stock             = 0
  const capacity          = 0
  const openOrders        = 0
  const proceeds30d       = 0
  const feedbackRating    = 0

  return {
    products,
    loading,
    error,
    totalSalesToday,
    activeListings,
    stock,
    capacity,
    openOrders,
    proceeds30d,
    feedbackRating
  }
}
