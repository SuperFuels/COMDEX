// frontend/pages/buyer/dashboard.tsx
import { useEffect, useState } from 'react'
import { NextPage } from 'next'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import Chart, { ChartPoint } from '@/components/Chart'

type Tab =
  | 'dealFlow'
  | 'notifications'
  | 'escrow'
  | 'deliveries'
  | 'orders'
  | 'supplierList'
  | 'products'

const BuyerDashboard: NextPage = () => {
  // 1) enforce login + buyer role
  useAuthRedirect('buyer')

  // 2) local state
  const [tab, setTab]             = useState<Tab>('dealFlow')
  const [chartData, setChartData] = useState<ChartPoint[]>([])
  const [deals, setDeals]         = useState<any[]>([])
  const [products, setProducts]   = useState<any[]>([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState<string | null>(null)

  // 3) fetch chart / deals / products
  useEffect(() => {
    async function load() {
      try {
        // • chart data (if endpoint exists)
        let pts: ChartPoint[] = []
        try {
          const chartRes = await api.get<{ price_per_kg: number }[]>('/products')
          pts = chartRes.data.map(p => ({
            // must match ChartPoint: time:number, value:number
            time:  Math.floor(Date.now() / 1000),
            value: p.price_per_kg,
          }))
        } catch {
          console.warn('No chart endpoint; skipping chart')
        }
        setChartData(pts)

        // • active deals
        try {
          const dealsRes = await api.get<any[]>('/deals')
          setDeals(dealsRes.data)
        } catch {
          console.warn('Failed to fetch deals; continuing')
        }

        // • marketplace listings
        try {
          const prodRes = await api.get<any[]>('/products')
          setProducts(prodRes.data)
        } catch {
          console.warn('Failed to fetch products; continuing')
        }
      } catch (e) {
        console.error('❌ Error loading buyer data', e)
        setError('Failed to load dashboard.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // 4) loading / error states
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
        <p className="text-red-500">{error}</p>
      </div>
    )
  }

  // 5) render
  return (
    <main className="min-h-screen bg-gray-50 p-6 max-w-7xl mx-auto">
      {/* live pricing chart */}
      <div className="bg-white p-4 rounded shadow mb-6">
        <h2 className="text-lg font-semibold mb-2">
          Live Ask Price (per tonne)
        </h2>
        <Chart data={chartData} />
      </div>

      {/* tab nav */}
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

      {/* tab panels */}
      {tab === 'dealFlow' && (
        <section className="bg-white p-4 rounded shadow">
          {deals.length === 0 ? (
            <p className="text-gray-500">🤝 No active deals.</p>
          ) : (
            <ul>
              {deals.map(d => (
                <li key={d.id} className="mb-2">
                  Deal #{d.id}: {d.product_title} – {d.status}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {tab === 'notifications' && (
        <section className="bg-white p-4 rounded shadow">
          <p className="text-gray-500">🔔 No notifications.</p>
        </section>
      )}

      {tab === 'escrow' && (
        <section className="bg-white p-4 rounded shadow">
          <p className="text-gray-500">🔒 Escrow empty.</p>
        </section>
      )}

      {tab === 'deliveries' && (
        <section className="bg-white p-4 rounded shadow">
          <p className="text-gray-500">🚚 No deliveries.</p>
        </section>
      )}

      {tab === 'orders' && (
        <section className="bg-white p-4 rounded shadow">
          <p className="text-gray-500">📦 No orders.</p>
        </section>
      )}

      {tab === 'supplierList' && (
        <section className="bg-white p-4 rounded shadow">
          <p className="text-gray-500">🏷️ No suppliers found.</p>
        </section>
      )}

      {tab === 'products' && (
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {products.map(p => (
            <div
              key={p.id}
              className="bg-white p-4 rounded shadow flex flex-col"
            >
              <img
                src={`${process.env.NEXT_PUBLIC_API_URL}${p.image_url}`}
                alt={p.title}
                className="h-40 w-full object-cover rounded mb-2"
                onError={e => { (e.target as any).src = '/placeholder.jpg' }}
              />
              <h3 className="text-lg font-semibold">{p.title}</h3>
              <p className="text-sm text-gray-700 mt-1">{p.description}</p>
              <p className="text-sm text-gray-500 mt-1">{p.origin_country}</p>
              <p className="text-lg font-bold mt-2">${p.price_per_kg}/kg</p>
              <button
                onClick={() => window.location.href = `/deals/create/${p.id}`}
                className="mt-auto bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
              >
                Contact Supplier
              </button>
            </div>
          ))}
        </section>
      )}
    </main>
  )
}

export default BuyerDashboard
