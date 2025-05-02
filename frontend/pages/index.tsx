// frontend/pages/index.tsx

import { useEffect, useState } from 'react'
import axios from 'axios'
import Link from 'next/link'
import type { NextPage } from 'next'

interface Product {
  id: number
  title: string
  description: string
  price_per_kg: number
  origin_country: string
  image_url: string
  category: string
}

const Home: NextPage = () => {
  const [products, setProducts] = useState<Product[]>([])
  const [search, setSearch] = useState('')

  // fetch all products (public)
  const fetchAll = async () => {
    try {
      const { data } = await axios.get<Product[]>(
        'http://localhost:8000/products'
      )
      setProducts(data)
    } catch (err) {
      console.error('❌ Failed to load products', err)
    }
  }

  // fetch only matching products
  const searchProducts = async (query: string) => {
    try {
      const { data } = await axios.get<Product[]>(
        `http://localhost:8000/products/search?query=${encodeURIComponent(
          query
        )}`
      )
      setProducts(data)
    } catch (err) {
      console.error('❌ Search failed', err)
    }
  }

  // whenever `search` changes, decide which to fetch
  useEffect(() => {
    if (search.trim()) {
      searchProducts(search.trim())
    } else {
      fetchAll()
    }
  }, [search])

  return (
    <div className="min-h-screen bg-white text-gray-900">
      {/* ─── Marketplace Search & Results ───────────────────────── */}
      <div className="mt-8 max-w-6xl mx-auto px-4 pb-12">
        <div className="mb-8 text-center">
          <h2 className="text-2xl font-bold mb-2">Explore the Marketplace</h2>
          <input
            type="text"
            placeholder="Search by title or category..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full max-w-md mx-auto p-2 border border-gray-300 rounded"
          />
        </div>

        {/* only when they've actively searched and found nothing */}
        {search.trim() && products.length === 0 && (
          <p className="text-center text-gray-500">No products found.</p>
        )}

        {/* show grid of results (or all products) if any exist */}
        {products.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {products.map((p) => (
              <div
                key={p.id}
                className="flex flex-col bg-white border border-gray-200 p-4 rounded"
              >
                <img
                  src={
                    p.image_url.startsWith('http')
                      ? p.image_url
                      : `http://localhost:8000${p.image_url}`
                  }
                  alt={p.title}
                  className="h-48 w-full object-cover rounded mb-4"
                  onError={(e) =>
                    ((e.currentTarget as HTMLImageElement).src =
                      '/placeholder.jpg')
                  }
                />
                <h3 className="font-semibold text-lg mb-1">{p.title}</h3>
                <p className="text-sm text-gray-700">{p.origin_country}</p>
                <p className="text-sm text-gray-500 mb-2">{p.category}</p>
                <p className="font-bold mb-4">${p.price_per_kg}/kg</p>
                <Link href={`/product/${p.id}`} passHref>
                  <button className="mt-auto w-full py-2 bg-blue-500 text-white rounded">
                    View Product
                  </button>
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Home

