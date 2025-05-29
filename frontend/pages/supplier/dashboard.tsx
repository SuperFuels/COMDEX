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
  // only suppliers allowed here
  useAuthRedirect('supplier')

  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchMyProducts = async () => {
      setLoading(true)
      try {
        // grab the JWT out of localStorage (or wherever you saved it)
        const token = localStorage.getItem('token')
        if (!token) {
          throw new Error('Not authenticated')
        }

        // attach it to your axios instance for this call
        const res = await api.get<Product[]>('/products/me', {
          headers: { Authorization: `Bearer ${token}` }
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

  // Stub metrics
  const totalSalesToday = 0
  const activeListings    = products.length
  const stock             = 0
  const capacity          = 0
  const openOrders        = 0
  const proceeds30d       = 0
  const feedbackRating    = 0

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-600">Loading dashboard…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-red-600">{error}</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="p-6 max-w-7xl mx-auto space-y-8">
        {/* Metrics cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
          {/* ... your existing metric cards ... */}
        </div>

        {/* Charts section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* ... chart placeholders ... */}
        </div>

        {/* My Listings Table */}
        <div className="bg-white shadow rounded p-4">
          <h2 className="text-lg font-semibold mb-4">My Listings</h2>
          {products.length === 0 ? (
            <p className="text-gray-500">You have no active listings yet.</p>
          ) : (
            <table className="min-w-full table-auto">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left">Title</th>
                  <th className="px-4 py-2 text-left">Category</th>
                  <th className="px-4 py-2 text-left">Origin</th>
                  <th className="px-4 py-2 text-right">Price / kg</th>
                  <th className="px-4 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id} className="border-t">
                    <td className="px-4 py-2">{p.title}</td>
                    <td className="px-4 py-2">{p.category}</td>
                    <td className="px-4 py-2">{p.origin_country}</td>
                    <td className="px-4 py-2 text-right">£{p.price_per_kg.toFixed(2)}</td>
                    <td className="px-4 py-2 text-right">
                      <Link href={`/products/edit/${p.id}`} prefetch={false}>
                        <a className="text-blue-600 hover:underline">Edit</a>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Sell product CTA */}
        <div className="text-right">
          <Link href="/products/new" prefetch={false}>
            <a className="inline-block bg-blue-600 text-white px-4 py-2 rounded">
              + Sell Product
            </a>
          </Link>
        </div>
      </main>
    </div>
  )
}