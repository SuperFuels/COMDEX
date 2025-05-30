// frontend/hooks/useSupplierDashboard.ts
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
    async function load() {
      setLoading(true)
      try {
        // fetch only your own products
        const res = await api.get<Product[]>('/products/me')
        const products = res.data

        // derive stub metrics — you can wire these up to real endpoints later
        const dashboard: SupplierDashboardData = {
          totalSalesToday: 0,
          activeListings: products.length,
          openOrders: 0,
          proceeds30d: 0,
          feedbackRating: 0,
          products
        }

        setData(dashboard)
      } catch (err) {
        console.error('useSupplierDashboard failed', err)
        setError('Unable to load dashboard data.')
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  return { data, loading, error }
}