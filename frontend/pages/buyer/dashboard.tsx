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

export default function BuyerDashboard(): JSX.Element {
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
      {/*
        ─────────────────────────────────────────────────────────────────────────────
        Main content (we add pb-16 so content doesn't get hidden behind the fixed bar)
        ─────────────────────────────────────────────────────────────────────────────
      */}
      <main className="max-w-7xl mx-auto px-5 pt-6 pb-16 space-y-6">
        {/* live pricing chart */}
        <div className="bg-white p-4 rounded shadow">
          <h2 className="text-lg font-semibold mb-2">
            Live Ask Price (per tonne)
          </h2>
          <Chart data={chartData} />
        </div>

        {/*
          ─────────────────────────────────────────────────────────────────────────────
          “Central Command” Two-Pane Layout (Text | Visual)
          ─────────────────────────────────────────────────────────────────────────────
        */}
        <div className="bg-white rounded shadow flex">
          {/* LEFT PANE: Text + Metrics + Buttons */}
          <div className="w-1/2 border-r border-gray-200 p-6 font-mono text-sm text-gray-800">
            <p className="mb-2">Hello, Buyer — welcome to Central Command.</p>
            <p className="mb-1">
              “Sales Today”: <span className="text-blue-600">0</span>
            </p>
            <p className="mb-1">
              “Open Orders”: <span className="text-green-600">0</span>
            </p>
            <p className="mb-1">
              “Pending Escrow”: <span className="text-purple-600">0</span>
            </p>
            <p className="mb-1">
              “Available Products”: <span className="text-blue-600">{products.length}</span>
            </p>
            <p className="mb-1">
              “Active Deals”: <span className="text-green-600">{deals.length}</span>
            </p>

            <div className="mt-4 border-t border-gray-200 pt-3 italic text-gray-600">
              Select one of the buttons below, or type a question in the terminal bar.
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              <button
                onClick={() => setTab('dealFlow')}
                className={`px-3 py-1 border border-black rounded text-sm ${
                  tab === 'dealFlow' ? 'bg-gray-100' : ''
                }`}
              >
                Deal Flow
              </button>
              <button
                onClick={() => setTab('notifications')}
                className={`px-3 py-1 border border-black rounded text-sm ${
                  tab === 'notifications' ? 'bg-gray-100' : ''
                }`}
              >
                Notifications
              </button>
              <button
                onClick={() => setTab('escrow')}
                className={`px-3 py-1 border border-black rounded text-sm ${
                  tab === 'escrow' ? 'bg-gray-100' : ''
                }`}
              >
                Escrow
              </button>
              <button
                onClick={() => setTab('deliveries')}
                className={`px-3 py-1 border border-black rounded text-sm ${
                  tab === 'deliveries' ? 'bg-gray-100' : ''
                }`}
              >
                Deliveries
              </button>
              <button
                onClick={() => setTab('orders')}
                className={`px-3 py-1 border border-black rounded text-sm ${
                  tab === 'orders' ? 'bg-gray-100' : ''
                }`}
              >
                Orders
              </button>
              <button
                onClick={() => setTab('supplierList')}
                className={`px-3 py-1 border border-black rounded text-sm ${
                  tab === 'supplierList' ? 'bg-gray-100' : ''
                }`}
              >
                Supplier List
              </button>
              <button
                onClick={() => setTab('products')}
                className={`px-3 py-1 border border-black rounded text-sm ${
                  tab === 'products' ? 'bg-gray-100' : ''
                }`}
              >
                Available Products
              </button>
            </div>
          </div>

          {/* RIGHT PANE: Placeholder for Visual Output */}
          <div className="w-1/2 p-6 flex items-center justify-center text-gray-500">
            <span>Select a button or ask a question to see visual output here.</span>
          </div>
        </div>

        {/*
          Below the two‐pane card, we can optionally show the “active tab” content:
          (For simplicity, you can render each <section> only when that tab is active.)
        */}
        <div>
          {tab === 'dealFlow' && (
            <section className="bg-white p-4 rounded shadow mt-4">
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
            <section className="bg-white p-4 rounded shadow mt-4">
              <p className="text-gray-500">🔔 No notifications.</p>
            </section>
          )}
          {tab === 'escrow' && (
            <section className="bg-white p-4 rounded shadow mt-4">
              <p className="text-gray-500">🔒 Escrow empty.</p>
            </section>
          )}
          {tab === 'deliveries' && (
            <section className="bg-white p-4 rounded shadow mt-4">
              <p className="text-gray-500">🚚 No deliveries.</p>
            </section>
          )}
          {tab === 'orders' && (
            <section className="bg-white p-4 rounded shadow mt-4">
              <p className="text-gray-500">📦 No orders.</p>
            </section>
          )}
          {tab === 'supplierList' && (
            <section className="bg-white p-4 rounded shadow mt-4">
              <p className="text-gray-500">🏷️ No suppliers found.</p>
            </section>
          )}
          {tab === 'products' && (
            <section className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
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
        </div>
      </main>

      {/*
        ─────────────────────────────────────────────────────────────────────────────
        FIXED TERMINAL BAR (identical sizing/positioning to the supplier’s version)
        ─────────────────────────────────────────────────────────────────────────────
      */}
      <div
        className="
          fixed bottom-0 left-5 right-5      /* 20px margin on left & right; matches supplier */
          bg-white
          border-t border-gray-300
          flex items-center
          h-12                                /* 3rem tall exactly */
          px-3                                /* horizontal padding */
          space-x-2
          z-50
        "
      >
        {/* LEFT HALF: Input + Send button */}
        <div className="flex items-center space-x-2 flex-1">
          <input
            type="text"
            placeholder="Type a question (e.g. “Build my report”)"
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

        {/* RIGHT HALF: Tab Buttons (static, no horizontal scrollbar) */}
        <div className="flex space-x-2">
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