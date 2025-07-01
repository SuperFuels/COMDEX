// frontend/pages/search.tsx
"use client"

import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import api from '@/lib/api'

interface Product {
  id: number
  title: string
  origin_country: string
  price_per_kg: number
  image_url: string
  owner_email: string
  change_pct: number    // decimal, e.g. 0.0123
  rating: number
}

export default function SearchPage() {
  const router = useRouter()
  const { query } = router.query as { query?: string }
  const [results, setResults] = useState<Product[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)

  useEffect(() => {
    if (!query) return
    setLoading(true)
    setError(null)

    api
      .get<Product[]>(
        `/products/search?query=${encodeURIComponent(query)}`
      )
      .then(res => {
        setResults(res.data)
      })
      .catch(() => {
        setError('Failed to load search results')
      })
      .finally(() => {
        setLoading(false)
      })
  }, [query])

  return (
    <div className="px-4 py-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">
        Search results for “{query}”
      </h1>

      {loading && <p>Loading…</p>}
      {error   && <p className="text-red-600">{error}</p>}
      {!loading && !error && results.length === 0 && (
        <p className="text-gray-500">No products found for “{query}”.</p>
      )}

      {results.length > 0 && (
        <div className="overflow-x-auto bg-white shadow rounded-lg">
          <table className="min-w-full divide-y divide-gray-200 table-auto">
            <thead className="bg-gray-50">
              <tr>
                {[
                  'Image',
                  'Product',
                  'Origin',
                  'Cost/kg',
                  'Supplier',
                  'Change %',
                  'Rating / 10',
                  'Details'
                ].map(col => (
                  <th
                    key={col}
                    scope="col"
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {results.map(p => (
                <tr key={p.id} className="hover:bg-gray-100">
                  {/* Image */}
                  <td className="px-6 py-4 whitespace-nowrap">
                    {p.image_url ? (
                      <Image
                        src={
                          p.image_url.startsWith('http')
                            ? p.image_url
                            : `${process.env.NEXT_PUBLIC_API_URL}${p.image_url}`
                        }
                        alt={p.title}
                        width={40}
                        height={40}
                        className="rounded"
                      />
                    ) : (
                      <div className="w-10 h-10 bg-gray-200 rounded flex items-center justify-center text-xs text-gray-500">
                        No Img
                      </div>
                    )}
                  </td>

                  {/* Title */}
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {p.title}
                  </td>

                  {/* Origin */}
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {p.origin_country}
                  </td>

                  {/* Price */}
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ${p.price_per_kg.toFixed(2)}
                  </td>

                  {/* Supplier */}
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {p.owner_email}
                  </td>

                  {/* Change % */}
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span
                      className={
                        p.change_pct >= 0
                          ? 'text-green-600 font-semibold'
                          : 'text-red-600 font-semibold'
                      }
                    >
                      {(p.change_pct * 100).toFixed(2)}%
                    </span>
                  </td>

                  {/* Rating */}
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {p.rating.toFixed(1)}
                  </td>

                  {/* Details */}
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                    <Link
                      href={`/products/${p.id}`}
                      className="inline-block px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

