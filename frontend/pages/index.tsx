// frontend/pages/index.tsx
import { useEffect, useState } from 'react'
import type { NextPage } from 'next'
import Link from 'next/link'

import api from '@/lib/api'
import { signInWithEthereum } from '@/lib/siwe'
import Chart, { ChartPoint } from '@/components/Chart'
import Navbar from '@/components/Navbar'

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
  const [products, setProducts]   = useState<Product[]>([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(false)
  const [selected, setSelected]   = useState<Product | null>(null)
  const [filters, setFilters]     = useState<string[]>([])
  const [jwt, setJwt]             = useState<string | null>(null)

  // 1) Load JWT
  useEffect(() => {
    const token = localStorage.getItem('jwt')
    if (token) {
      setJwt(token)
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    }
  }, [])

  // 2) Fetch products when jwt changes
  useEffect(() => {
    setLoading(true)
    api.get<Product[]>('/products')
      .then(({ data }) => {
        setProducts(data)
        if (data.length) setSelected(data[0])
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [jwt])

  // 3) Chart data
  const chartData: ChartPoint[] = selected
    ? Array.from({ length: 24 }, (_, i) => ({
        time:  Math.floor(Date.now() / 1000) - (23 - i) * 3600,
        value: selected.price_per_kg * 1000 + (Math.random() - 0.5) * 500,
      }))
    : []

  // 4) Filters
  const countries = Array.from(new Set(products.map(p => p.origin_country)))
  const visibleProducts = filters.length
    ? products.filter(p => filters.includes(p.origin_country))
    : products

  // 5) Connect
  const handleLogin = async () => {
    try {
      const { token } = await signInWithEthereum()
      setJwt(token)
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      localStorage.setItem('jwt', token)
    } catch (err) {
      console.error('Login failed', err)
      alert('Failed to sign in. Check console for details.')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 py-4 flex justify-end">
        {!jwt ? (
          <button
            onClick={handleLogin}
            className="px-4 py-2 bg-blue-600 text-white rounded"
          >
            Connect Wallet
          </button>
        ) : (
          <Link href="/dashboard">
            <a className="px-4 py-2 bg-green-600 text-white rounded">
              Dashboard
            </a>
          </Link>
        )}
      </div>

      <main className="max-w-7xl mx-auto grid grid-cols-12 gap-6 px-4 py-6">
        {/* main & sidebar… exactly as before */}
      </main>
    </div>
  )
}

export default Home