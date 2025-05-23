// frontend/pages/index.tsx
import { useEffect, useState } from 'react'
import type { NextPage } from 'next'
import api from '@/lib/api'
import { signInWithEthereum } from '@/lib/siwe'
import Chart, { ChartPoint } from '@/components/Chart'
import Link from 'next/link'

interface Product {
  id: number
  title: string
  price_per_kg: number
  origin_country: string
  category: string
  change_pct: number
  rating: number
}

const Home: NextPage = () => {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [selected, setSelected] = useState<Product | null>(null)
  const [filters, setFilters] = useState<string[]>([])
  const [jwt, setJwt] = useState<string | null>(null)

  // 0) On mount, load any saved JWT
  useEffect(() => {
    const token = localStorage.getItem('jwt')
    if (token) {
      setJwt(token)
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    }
  }, [])

  // 1) Fetch products once _and_ whenever we log in
  useEffect(() => {
    setLoading(true)
    api
      .get<Product[]>('/products')
      .then(({ data }) => {
        setProducts(data)
        if (data.length) setSelected(data[0])
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [jwt])

  // 2) Build chart data for the selected product
  const chartData: ChartPoint[] = selected
    ? Array.from({ length: 24 }, (_, i) => ({
        time: Math.floor(Date.now() / 1000) - (23 - i) * 3600,
        value: selected.price_per_kg * 1000 + (Math.random() - 0.5) * 500,
      }))
    : []

  // 3) Country filters
  const countries = Array.from(new Set(products.map((p) => p.origin_country)))
  const visibleProducts = filters.length
    ? products.filter((p) => filters.includes(p.origin_country))
    : products

  // 4) Connect-wallet handler
  const handleLogin = async () => {
    try {
      const token = await signInWithEthereum()
      setJwt(token)
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      localStorage.setItem('jwt', token)
    } catch (err) {
      console.error('Login failed', err)
      alert('Failed to sign in. Check console for details.')
    }
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-blue-600 text-white">
        <h1 className="text-2xl font-bold">COMDEX Marketplace</h1>
        {jwt ? (
          <span className="px-4 py-2 bg-blue-800 rounded">Connected</span>
        ) : (
          <button
            onClick={handleLogin}
            className="px-4 py-2 bg-white text-blue-600 rounded hover:bg-gray-100"
          >
            Connect Wallet
          </button>
        )}
      </header>

      <main className="max-w-7xl mx-auto grid grid-cols-12 gap-6 px-4 py-6">
        {/* Main */}
        <div className="col-span-12 md:col-span-9 space-y-6">
          {loading ? (
            <p className="text-center">Loading…</p>
          ) : error ? (
            <p className="text-center text-red-500">
              Failed to load products.
            </p>
          ) : (
            <>
              {/* Chart */}
              <div className="bg-white border rounded-lg shadow-sm p-4">
                {selected ? (
                  <Chart data={chartData} height={300} />
                ) : (
                  <p className="text-center text-gray-500">
                    No product selected.
                  </p>
                )}
              </div>

              {/* Products Table */}
              <div className="overflow-x-auto bg-white border rounded-lg shadow-sm">
                <table className="min-w-full table-auto">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left">Product</th>
                      <th className="px-4 py-2 text-left">Origin</th>
                      <th className="px-4 py-2 text-left">Category</th>
                      <th className="px-4 py-2 text-right">Price/kg</th>
                      <th className="px-4 py-2 text-right">Change%</th>
                      <th className="px-4 py-2 text-center">Rating</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleProducts.map((p) => (
                      <tr
                        key={p.id}
                        className="border-t hover:bg-gray-50 cursor-pointer"
                        onClick={() => setSelected(p)}
                      >
                        <td className="px-4 py-2">
                          <Link href={`/products/${p.id}`}>
                            <a className="text-blue-600 hover:underline">
                              {p.title}
                            </a>
                          </Link>
                        </td>
                        <td className="px-4 py-2">{p.origin_country}</td>
                        <td className="px-4 py-2">{p.category}</td>
                        <td className="px-4 py-2 text-right">
                          £{p.price_per_kg.toFixed(2)}
                        </td>
                        <td
                          className={`px-4 py-2 text-right ${
                            p.change_pct >= 0
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          {p.change_pct >= 0 ? '↑' : '↓'}{' '}
                          {(Math.abs(p.change_pct) * 100).toFixed(2)}%
                        </td>
                        <td className="px-4 py-2 text-center">
                          {p.rating.toFixed(1)}/5
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        {/* Sidebar */}
        <aside className="col-span-12 md:col-span-3 space-y-6">
          {selected && (
            <div className="bg-white border rounded-lg shadow-sm p-4">
              <h2 className="text-xl font-semibold">{selected.title}</h2>
              <p className="text-3xl font-bold">
                £{(selected.price_per_kg * 1000).toFixed(2)}/t{' '}
                <span
                  className={
                    selected.change_pct >= 0 ? 'text-green-600' : 'text-red-600'
                  }
                >
                  {selected.change_pct >= 0 ? '↑' : '↓'}{' '}
                  {(Math.abs(selected.change_pct) * 100).toFixed(2)}%
                </span>
              </p>
              <div className="flex space-x-3 text-gray-500">
                <button title="Copy link">🔗</button>
                <button title="Twitter">🐦</button>
                <button title="Telegram">✈️</button>
              </div>
            </div>
          )}

          <div className="bg-white border rounded-lg shadow-sm p-4">
            <h3 className="text-lg font-medium mb-2">Country Filters</h3>
            <ul className="space-y-1">
              {countries.map((country) => (
                <li key={country}>
                  <label className="inline-flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={filters.includes(country)}
                      onChange={() =>
                        setFilters((prev) =>
                          prev.includes(country)
                            ? prev.filter((x) => x !== country)
                            : [...prev, country]
                        )
                      }
                      className="form-checkbox h-4 w-4 text-blue-500"
                    />
                    <span>{country}</span>
                  </label>
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </main>
    </div>
  )
}

export default Home
