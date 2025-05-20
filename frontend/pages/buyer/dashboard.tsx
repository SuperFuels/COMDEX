// frontend/pages/buyer/dashboard.tsx

import { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import Navbar from '@/components/Navbar'
import Chart, { ChartPoint } from '@/components/Chart'
import api from '@/lib/api'

type Tab =
  | 'dealFlow'
  | 'notifications'
  | 'escrow'
  | 'deliveries'
  | 'orders'
  | 'supplierList'
  | 'products'

export default function BuyerDashboard() {
  const router = useRouter()
  const [tab, setTab] = useState<Tab>('dealFlow')
  const [chartData, setChartData] = useState<ChartPoint[]>([])
  const [deals, setDeals] = useState<any[]>([])
  const [products, setProducts] = useState<any[]>([])
  const [loading, setLoading] = useState<boolean>(true)

  // ─── Guard + Role Check ───────────────────────────────
  useEffect(() => {
    const safeguard = async () => {
      const token = localStorage.getItem('token')
      if (!token) {
        await router.replace('/login')
        return
      }

      try {
        const res = await api.get(
          '/auth/role',
          { headers: { Authorization: `Bearer ${token}` } }
        )
        if (res.data.role !== 'buyer') {
          await router.replace('/login')
          return
        }
      } catch {
        await router.replace('/login')
      }
    }

    safeguard()
  }, [router])

  // ─── Fetch chart points, deals & products ──────────────
  useEffect(() => {
    const fetchAll = async () => {
      const token = localStorage.getItem('token')
      if (!token) {
        await router.replace('/login')
        return
      }

      try {
        // • Chart data (fallback to /products for pricing)
        let pts: ChartPoint[] = []
        try {
          const chartRes = await api.get(
            '/products',
            { headers: { Authorization: `Bearer ${token}` } }
          )
          pts = chartRes.data.map((p: any) => ({
            x: new Date().toLocaleTimeString(),
            y: p.price_per_kg,
          }))
        } catch {
          console.warn('No chart series endpoint, skipping chart')
        }
        setChartData(pts)

        // • Active deals
        const dealsRes = await api.get(
          '/deals',
          { headers: { Authorization: `Bearer ${token}` } }
        )
        setDeals(dealsRes.data)

        // • Marketplace listings
        const prodRes = await api.get(
          '/products',
          { headers: { Authorization: `Bearer ${token}` } }
        )
        setProducts(prodRes.data)
      } finally {
        setLoading(false)
      }
    }

    fetchAll()
  }, [router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-600">Loading dashboard…</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <main className="p-6 max-w-7xl mx-auto">
        <div className="bg-white p-4 rounded shadow mb-6">
          <h2 className="text-lg font-semibold mb-2">
            Live Ask Price (per tonne)
          </h2>
          <Chart data={chartData} />
        </div>

        <nav className="mb-4 border-b">
          {[
            ['Deal Flow', 'dealFlow'],
            ['Notifications', 'notifications'],
            ['Escrow', 'escrow'],
            ['Deliveries', 'deliveries'],
            ['Orders', 'orders'],
            ['Supplier List', 'supplierList'],
            ['Available Products', 'products'],
          ].map(([label, id]) => (
            <button
              key={id}
              onClick={() => setTab(id as Tab)}
              className={`px-4 py-2 -mb-px ${
                tab === id
                  ? 'border-b-2 border-blue-600 font-semibold'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              {label}
            </button>
          ))}
        </nav>

        {tab === 'dealFlow' && (
          <div className="bg-white p-4 rounded shadow">
            {deals.length === 0 ? (
              <p className="text-gray-500">🤝 No active deals.</p>
            ) : (
              <ul>
                {deals.map((d) => (
                  <li key={d.id} className="mb-2">
                    Deal #{d.id}: {d.product_title} – {d.status}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {tab === 'notifications' && (
          <div className="bg-white p-4 rounded shadow">
            <p className="text-gray-500">🔔 No notifications.</p>
          </div>
        )}

        {tab === 'escrow' && (
          <div className="bg-white p-4 rounded shadow">
            <p className="text-gray-500">🔒 Escrow empty.</p>
          </div>
        )}

        {tab === 'deliveries' && (
          <div className="bg-white p-4 rounded shadow">
            <p className="text-gray-500">🚚 No deliveries.</p>
          </div>
        )}

        {tab === 'orders' && (
          <div className="bg-white p-4 rounded shadow">
            <p className="text-gray-500">📦 No orders.</p>
          </div>
        )}

        {tab === 'supplierList' && (
          <div className="bg-white p-4 rounded shadow">
            <p className="text-gray-500">🏷️ No suppliers found.</p>
          </div>
        )}

        {tab === 'products' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {products.map((p) => (
              <div
                key={p.id}
                className="bg-white p-4 rounded shadow flex flex-col"
              >
                <img
                  src={`${process.env.NEXT_PUBLIC_API_URL}${p.image_url}`}
                  alt={p.title}
                  className="h-40 w-full object-cover rounded mb-2"
                  onError={(e) => {
                    ;(e.target as HTMLImageElement).src = '/placeholder.jpg'
                  }}
                />
                <h2 className="text-lg font-semibold">{p.title}</h2>
                <p className="text-sm text-gray-700 mt-1">{p.description}</p>
                <p className="text-sm text-gray-500 mt-1">
                  {p.origin_country}
                </p>
                <p className="text-lg font-bold mt-2">
                  ${p.price_per_kg}/kg
                </p>
                <button
                  onClick={() => router.push(`/deals/create/${p.id}`)}
                  className="mt-auto bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                >
                  Contact Supplier
                </button>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

