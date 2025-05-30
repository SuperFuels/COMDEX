// frontend/pages/products/index.tsx

import { useEffect, useState } from 'react'
import Sidebar from '@/components/Sidebar'
import api from '@/lib/api'

interface Product {
  id: number
  title: string
  origin_country: string
  category: string
  price_per_kg: number
  image_url: string
}

export default function ProductList() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchProducts = async () => {
      setLoading(true)
      try {
        const res = await api.get<Product[]>('/products')
        setProducts(res.data)
      } catch (err) {
        console.error('Failed to load products', err)
        setError('Unable to load products.')
      } finally {
        setLoading(false)
      }
    }
    fetchProducts()
  }, [])

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="p-8 w-full">
        <h1 className="text-2xl font-bold mb-4">Product Listing</h1>

        {loading && <p className="text-gray-600">Loading products…</p>}

        {error && <p className="text-red-600">{error}</p>}

        {!loading && !error && products.length === 0 && (
          <p className="text-gray-500">No products found.</p>
        )}

        {!loading && !error && products.length > 0 && (
          <table className="min-w-full bg-white shadow rounded overflow-hidden">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-2 text-left">Title</th>
                <th className="px-4 py-2 text-left">Category</th>
                <th className="px-4 py-2 text-left">Origin</th>
                <th className="px-4 py-2 text-right">Price / kg</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => (
                <tr key={p.id} className="border-t">
                  <td className="px-4 py-2">{p.title}</td>
                  <td className="px-4 py-2">{p.category}</td>
                  <td className="px-4 py-2">{p.origin_country}</td>
                  <td className="px-4 py-2 text-right">
                    £{p.price_per_kg.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}