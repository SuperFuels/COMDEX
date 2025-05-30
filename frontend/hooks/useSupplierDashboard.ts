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
  totalSalesToday: number
  activeListings: number
  stock: number
  capacity: number
  openOrders: number
  proceeds30d: number
  feedbackRating: number
  products: Product[]
}

export default function useSupplierDashboard() {
  const [data, setData] = useState<SupplierDashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const token = localStorage.getItem('token')
        if (!token) throw new Error('Not authenticated')

        const res = await api.get<Product[]>('/products/me', {
          headers: { Authorization: \`Bearer \${token}\` }
        })
        const products = res.data

        setData({
          totalSalesToday: 0,
          activeListings: products.length,
          stock: 0,
          capacity: 0,
          openOrders: 0,
          proceeds30d: 0,
          feedbackRating: 0,
          products
        })
      } catch (err) {
        console.error('❌ Failed to load dashboard data', err)
        setError('Failed to load dashboard data.')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  return { data, loading, error }
}
