// frontend/pages/buyer/dashboard.tsx

import { useEffect, useState } from 'react'
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

export default function BuyerDashboard() {
  // 1) enforce that only “buyer” can view this page
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
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-600">Loading dashboard…</p>
      </div>
    )
  }
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-red-500">{error}</p>
      </div>
    )
  }

  // 5) render
  return (
    <div className="min-h-screen bg-gray-50 relative">
      {/* ───────────────────────────────────────────────────────────────────────────── */}
      {/* Main content (we add pb-16 so content doesn't get hidden behind the fixed bar) */}
      {/* ───────────────────────────────────────────────────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-5 pt-6 pb-16 space-y-6">
        {/* ─── 1) Live Ask Price Chart ───────────────────────────────────────────────── */}
        <div className="bg-white p-4 rounded shadow">
          <h2 className="text-lg font-semibold mb-2">
            Live Ask Price (per tonne)
          </h2>
          <Chart data={chartData} />
        </div>

        {/* ─── 2) Two‐Pane “Text | Visual” Split ────────────────────────────────────────── */}
        <div className="flex bg-white rounded shadow overflow-hidden">
          {/* Left Pane: Text / Metrics / Tabbed Content */}
          <div className="w-1/2 border-r border-gray-200 p-6 space-y-4">
            {/* Greeting & Metrics */}
            <div className="font-mono text-base text-gray-800 space-y-1">
              <p>Hello, Buyer — welcome to Central Command.</p>
              <p>“Sales Today”: 0</p>
              <p>“Open Orders”: 0</p>
              <p>“Pending Escrow”: 0</p>
              <p>“Available Products”: {products.length}</p>
              <p>“Active Deals”: {deals.length}</p>
            </div>

            <div className="pt-4 border-t border-gray-200">
              <p className="italic text-gray-600">
                Select one of the buttons below, or type a question in the input bar.
              </p>
            </div>

            {/* Tab Navigation */}
            <nav className="flex flex-wrap gap-2 border-b pb-2 pt-2">
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
                  className={`
                    px-3 py-1 -mb-px text-sm
                    ${
                      tab === id
                        ? 'border-b-2 border-blue-600 font-semibold text-gray-800'
                        : 'text-gray-600 hover:text-gray-800'
                    }
                  `}
                >
                  {label}
                </button>
              ))}
            </nav>

            {/* Tab Panels */}
            <div className="pt-4">
              {tab === 'dealFlow' && (
                <section>
                  {deals.length === 0 ? (
                    <p className="text-gray-500">🤝 No active deals.</p>
                  ) : (
                    <ul className="space-y-2">
                      {deals.map(d => (
                        <li key={d.id} className="text-gray-800">
                          Deal #{d.id}: {d.product_title} – {d.status}
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              )}

              {tab === 'notifications' && (
                <section>
                  <p className="text-gray-500">🔔 No notifications.</p>
                </section>
              )}

              {tab === 'escrow' && (
                <section>
                  <p className="text-gray-500">🔒 Escrow empty.</p>
                </section>
              )}

              {tab === 'deliveries' && (
                <section>
                  <p className="text-gray-500">🚚 No deliveries.</p>
                </section>
              )}

              {tab === 'orders' && (
                <section>
                  <p className="text-gray-500">📦 No orders.</p>
                </section>
              )}

              {tab === 'supplierList' && (
                <section>
                  <p className="text-gray-500">🏷️ No suppliers found.</p>
                </section>
              )}

              {tab === 'products' && (
                <section className="grid grid-cols-1 gap-4">
                  {products.map(p => (
                    <div key={p.id} className="flex items-center space-x-4">
                      <img
                        src={`${process.env.NEXT_PUBLIC_API_URL}${p.image_url}`}
                        alt={p.title}
                        className="h-16 w-16 object-cover rounded"
                        onError={e => { (e.target as any).src = '/placeholder.jpg' }}
                      />
                      <div className="flex-1">
                        <h3 className="text-gray-800 font-medium">{p.title}</h3>
                        <p className="text-gray-600 text-sm">£{p.price_per_kg}/kg</p>
                      </div>
                      <button
                        onClick={() => window.location.href = `/deals/create/${p.id}`}
                        className="bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 text-sm"
                      >
                        Contact
                      </button>
                    </div>
                  ))}
                </section>
              )}
            </div>
          </div>

          {/* Right Pane: Visual Output Placeholder */}
          <div className="w-1/2 p-6 flex items-center justify-center text-gray-500">
            <p>Select a button or ask a question to see visual output here.</p>
          </div>
        </div>
      </main>

      {/* ───────────────────────────────────────────────────────────────────────────── */}
      {/* FIXED TERMINAL BAR (identical to supplier) */}
      {/* ───────────────────────────────────────────────────────────────────────────── */}
      <div
        className="
          fixed bottom-0 left-0 right-0
          bg-white
          border-t border-gray-300
          flex items-center
          h-12
          px-5
          z-50
        "
      >
        {/* ── LEFT SIDE: Text Input + Send Button ───────────────────────────────── */}
        <div className="flex items-center space-x-2 flex-1">
          <input
            type="text"
            placeholder="Type a question (e.g. “Build my sales report”)"
            className="
              flex-1
              h-10
              px-3
              border border-black rounded
              text-gray-700 text-sm
              placeholder-gray-400
              focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent
            "
          />
          <button
            className="
              h-10
              px-4
              bg-black text-white
              font-medium text-sm
              rounded
              hover:bg-gray-800
              focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-1
              transition
            "
          >
            Send
          </button>
        </div>

        {/* Vertical divider down the middle */}
        <div className="w-px bg-gray-300 h-6 mx-3 self-center"></div>

        {/* ── RIGHT SIDE: Static Buttons (no horizontal scroll) ─────────────────── */}
        <div className="flex items-center space-x-2">
          <button className="px-3 py-1 border border-black rounded text-sm whitespace-nowrap">
            Deal Flow
          </button>
          <button className="px-3 py-1 border border-black rounded text-sm whitespace-nowrap">
            Shipments
          </button>
          <button className="px-3 py-1 border border-black rounded text-sm whitespace-nowrap">
            Messages
          </button>
          <button className="px-3 py-1 border border-black rounded text-sm whitespace-nowrap">
            Escrow
          </button>
          <button className="px-3 py-1 border border-black rounded text-sm whitespace-nowrap">
            Contracts
          </button>
          <button className="px-3 py-1 border border-black rounded text-sm whitespace-nowrap">
            Suppliers
          </button>
          <button className="px-3 py-1 border border-black rounded text-sm whitespace-nowrap">
            Products
          </button>
        </div>
      </div>
    </div>
  )
}