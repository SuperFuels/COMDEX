// frontend/pages/dashboard.tsx

import { useEffect, useState } from 'react'
import Link from 'next/link'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'

interface Product {
  id: number
  title: string
  category: string
  origin_country: string
  price_per_kg: number
  image_url: string
}

export default function SupplierDashboard() {
  useAuthRedirect('supplier')

  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchMyProducts = async () => {
      try {
        const res = await api.get<Product[]>('/products/me')
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

  // Stub metrics
  const totalSalesToday = 0
  const activeListings = products.length
  const stock = 0
  const capacity = 0
  const openOrders = 0
  const proceeds30d = 0
  const feedbackRating = 0

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-600">Loading dashboard…</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="p-6 max-w-7xl mx-auto space-y-8">
        {/* Metrics cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          <div className="bg-white shadow rounded p-4">
            <p className="text-sm text-gray-500">My business</p>
            <p className="text-2xl font-bold">£{totalSalesToday}</p>
            <p className="text-xs text-gray-400">Today's sales</p>
          </div>
          <div className="bg-white shadow rounded p-4">
            <p className="text-sm text-gray-500">Products</p>
            <p className="text-2xl font-bold">{activeListings}</p>
            <p className="text-xs text-gray-400">Active listings</p>
          </div>
          <div className="bg-white shadow rounded p-4">
            <p className="text-sm text-gray-500">Inventory</p>
            <p className="text-2xl font-bold">{stock}/{capacity}</p>
            <p className="text-xs text-gray-400">Stock / capacity</p>
          </div>
          <div className="bg-white shadow rounded p-4">
            <p className="text-sm text-gray-500">Orders</p>
            <p className="text-2xl font-bold">{openOrders}</p>
            <p className="text-xs text-gray-400">Open orders</p>
          </div>
          <div className="bg-white shadow rounded p-4">
            <p className="text-sm text-gray-500">Payments</p>
            <p className="text-2xl font-bold">£{proceeds30d}</p>
            <p className="text-xs text-gray-400">Proceeds (30d)</p>
          </div>
          <div className="bg-white shadow rounded p-4">
            <p className="text-sm text-gray-500">Customers</p>
            <p className="text-2xl font-bold">{feedbackRating}</p>
            <p className="text-xs text-gray-400">Feedback rating</p>
          </div>
        </div>

        {/* Charts section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white shadow rounded p-4">
            <h2 className="text-lg font-semibold mb-2">Sales Over Time</h2>
            <div className="h-48 bg-gray-100 flex items-center justify-center text-gray-400">
              Chart placeholder
            </div>
          </div>
          <div className="bg-white shadow rounded p-4">
            <h2 className="text-lg font-semibold mb-2">Orders Over Time</h2>
            <div className="h-48 bg-gray-100 flex items-center justify-center text-gray-400">
              Chart placeholder
            </div>
          </div>
        </div>

        {/* Sell product CTA */}
        <div className="text-right">
          <Link href="/products/new" prefetch={false} className="inline-block bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700">
            + Sell Product
          </Link>
        </div>
      </main>
    </div>
  )
}

