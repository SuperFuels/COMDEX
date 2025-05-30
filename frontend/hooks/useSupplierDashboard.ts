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

export interface DashboardMetrics {
  totalSalesToday: number
  activeListings: number
  stock: number
  capacity: number
  openOrders: number
  proceeds30d: number
  feedbackRating: number
}

export function useSupplierDashboard() {
  const [products, setProducts] = useState<Product[]>([])
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    totalSalesToday: 0,
    activeListings: 0,
    stock: 0,
    capacity: 0,
    openOrders: 0,
    proceeds30d: 0,
    feedbackRating: 0,
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        const token = localStorage.getItem('token')
        if (!token) throw new Error('Not authenticated')

        const [prodRes, metricRes] = await Promise.all([
          api.get<Product[]>('/products/me', { headers: { Authorization: `Bearer ${token}` } }),
          api.get<DashboardMetrics>('/dashboard/supplier', { headers: { Authorization: `Bearer ${token}` } }),
        ])

        setProducts(prodRes.data)
        setMetrics(metricRes.data)
      } catch (e) {
        console.error('Dashboard error', e)
        setError('Failed to load dashboard data.')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  return { products, metrics, loading, error }
}
