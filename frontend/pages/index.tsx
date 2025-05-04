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
  change_pct: number    // ← new
  rating: number        // ← new
}

const Home: NextPage = () => {
  const [products, setProducts] = useState<Product[]>([])

  useEffect(() => {
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
    fetchAll()
  }, [])

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <div className="mt-8 max-w-6xl mx-auto px-4 pb-12">
        <div className="mb-8 text-center">
          <h2 className="text-2xl font-bold mb-2">Explore the Marketplace</h2>
          <form action="/search" method="get" className="flex justify-center">
            <input
              name="query"
              type="text"
              placeholder="Search by title or category..."
              className="w-full max-w-md p-2 border border-gray-300 rounded"
            />
            <button
              type="submit"
              className="ml-2 py-2 px-4 bg-blue-500 text-white rounded"
            >
              Search
            </button>
          </form>
        </div>

        {products.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {products.map((p) => (
              <div
                key={p.id}
                className="flex flex-col bg-white border border-gray-200 p-4 rounded-lg"
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
                <p className="font-bold mb-2">${p.price_per_kg.toFixed(2)}/kg</p>
                <div className="flex items-center mb-4 space-x-4">
                  <span className="text-green-600 font-medium">
                    {(p.change_pct * 100).toFixed(2)}%
                  </span>
                  <span className="text-yellow-600 font-medium">
                    {p.rating.toFixed(1)}/10
                  </span>
                </div>
                <Link
                  href={`/products/${p.id}`}
                  className="mt-auto w-full py-2 bg-blue-500 text-white rounded text-center"
                >
                  View Product
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

