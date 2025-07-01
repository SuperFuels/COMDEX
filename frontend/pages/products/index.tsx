// File: frontend/pages/products/index.tsx
"use client"

import { useEffect, useState } from 'react'
import api from '@/lib/api'

interface Product {
  id: number
  title: string
  origin_country: string
  category: string
  price_per_kg: number
  image_url?: string
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
    <main className="bg-bg-page min-h-screen pt-0">
      <div className="max-w-7xl mx-auto p-8">
        <h1 className="text-2xl font-semibold text-text mb-4">
          Product Listing
        </h1>

        {loading && (
          <p className="text-text-secondary">Loading products…</p>
        )}

        {error && (
          <p className="text-red-600">{error}</p>
        )}

        {!loading && !error && products.length === 0 && (
          <p className="text-text-secondary">No products found.</p>
        )}

        {!loading && !error && products.length > 0 && (
          <div className="overflow-x-auto">
            <table className="min-w-full bg-white shadow rounded-lg overflow-hidden">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left text-text-secondary">
                    Title
                  </th>
                  <th className="px-4 py-2 text-left text-text-secondary">
                    Category
                  </th>
                  <th className="px-4 py-2 text-left text-text-secondary">
                    Origin
                  </th>
                  <th className="px-4 py-2 text-right text-text-secondary">
                    Price / kg
                  </th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr
                    key={p.id}
                    className="border-t border-border-light dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                  >
                    <td className="px-4 py-2 text-text">{p.title}</td>
                    <td className="px-4 py-2 text-text">{p.category}</td>
                    <td className="px-4 py-2 text-text">{p.origin_country}</td>
                    <td className="px-4 py-2 text-right text-text">
                      £{p.price_per_kg.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  )
}