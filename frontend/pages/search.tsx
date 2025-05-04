// frontend/pages/search.tsx

import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import axios from 'axios'
import Link from 'next/link'

interface Product {
  id: number
  title: string
  origin_country: string
  price_per_kg: number
  image_url: string
  owner_email: string        // supplier’s email from backend
  change_pct: number         // ← new
  rating: number             // ← new
}

export default function SearchPage() {
  const router = useRouter()
  const { query } = router.query as { query?: string }
  const [results, setResults] = useState<Product[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!query) return
    setLoading(true)
    axios
      .get<Product[]>(
        `http://localhost:8000/products/search?query=${encodeURIComponent(query)}`
      )
      .then(res => setResults(res.data))
      .catch(() => setError('Failed to load search results'))
      .finally(() => setLoading(false))
  }, [query])

  return (
    <div className="max-w-5xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">
        Search results for “{query}”
      </h1>

      {loading && <p>Loading…</p>}
      {error && <p className="text-red-600">{error}</p>}
      {!loading && !error && results.length === 0 && (
        <p className="text-gray-500">No suppliers found for “{query}”.</p>
      )}

      {results.length > 0 && (
        <table className="min-w-full border-collapse mt-4">
          <thead>
            <tr className="bg-gray-200">
              <th className="border px-4 py-2">Image</th>
              <th className="border px-4 py-2">Product</th>
              <th className="border px-4 py-2">Origin</th>
              <th className="border px-4 py-2">Cost/kg</th>
              <th className="border px-4 py-2">Supplier</th>
              <th className="border px-4 py-2">Change %</th>
              <th className="border px-4 py-2">Rating /10</th>
              <th className="border px-4 py-2">Details</th>
            </tr>
          </thead>
          <tbody>
            {results.map((p, i) => (
              <tr
                key={p.id}
                className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
              >
                <td className="border px-4 py-2">
                  <img
                    src={
                      p.image_url.startsWith('http')
                        ? p.image_url
                        : `http://localhost:8000${p.image_url}`
                    }
                    alt={p.title}
                    className="h-10 w-10 object-cover rounded"
                   />
                </td>
                <td className="border px-4 py-2">{p.title}</td>
                <td className="border px-4 py-2">{p.origin_country}</td>
                <td className="border px-4 py-2">
                  ${p.price_per_kg.toFixed(2)}
                </td>
                <td className="border px-4 py-2">{p.owner_email}</td>
                <td className="border px-4 py-2 text-green-600">
                  {(p.change_pct * 100).toFixed(2)}%
                </td>
                <td className="border px-4 py-2 text-yellow-600">
                  {p.rating.toFixed(1)}
                </td>
                <td className="border px-4 py-2">
                  <Link
                    href={`/products/${p.id}`}
                    className="inline-block bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded"
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

