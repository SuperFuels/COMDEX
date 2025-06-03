// frontend/pages/buyer/dashboard.tsx
import { useEffect, useState } from 'react'
import { NextPage } from 'next'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import { ChartPoint } from '@/components/Chart'

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
            // must match ChartPoint: { time: number; value: number }
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
      {/* Spacer for sticky navbar (height = 4rem) */}
      {/* ───────────────────────────────────────────────────────────────────────────── */}
      <div className="h-16" />

      {/* ───────────────────────────────────────────────────────────────────────────── */}
      {/* Two‐Panel “Terminal” Section (Text | Visual) */}
      {/* ───────────────────────────────────────────────────────────────────────────── */}
      <div className="flex max-w-7xl mx-auto px-6 py-4">
        {/* ── Left Panel: Monospace “Text” Output ─────────────────────────────────── */}
        <div className="flex-1 pr-4">
          <div className="font-mono text-text dark:text-text-secondary text-sm leading-relaxed">
            <p className="mb-2">Hello, Kevin — welcome to Buyer Central Command.</p>
            <p>“Active Deals”: <span className="text-green-600">{deals.length}</span></p>
            <p>“Available Products”: <span className="text-blue-600">{products.length}</span></p>
            <p>
              “Latest Price”:{' '}
              <span className="text-purple-600">
                {chartData.length > 0 ? `$${chartData[chartData.length - 1].value}` : '$0'}
              </span>
            </p>
            <p className="mt-2 italic text-text-secondary dark:text-text-secondary">
              Select one of the buttons below, or type a question in the input bar.
            </p>
          </div>
        </div>

        {/* ── Vertical Divider ─────────────────────────────────────────────────────── */}
        <div className="border-l border-gray-300"></div>

        {/* ── Right Panel: Visual Output Placeholder ───────────────────────────────── */}
        <div className="flex-1 pl-4">
          <div className="flex h-full items-center justify-center text-text-secondary dark:text-text-secondary text-sm">
            Select a button or ask a question to see visual output here.
          </div>
        </div>
      </div>

      {/* ───────────────────────────────────────────────────────────────────────────── */}
      {/* FIXED TERMINAL BAR (Buyer) */}
      {/* ───────────────────────────────────────────────────────────────────────────── */}
      <div
        className="
          fixed bottom-0 left-0 right-0
          bg-white
          border-t border-gray-300
          flex items-center
          h-14                    /* 3.5rem = 56px total height */
          px-6
          z-50
        "
      >
        <div className="w-full max-w-7xl mx-auto flex items-center justify-between">
          {/* ── LEFT HALF: Input + Send ─────────────────────────────────────────── */}
          <div className="flex items-center w-full max-w-[calc(50%_-_1rem)] pr-4">
            <input
              type="text"
              placeholder="Type a question (e.g. “Build my report”)"
              className="
                flex-1
                h-10
                px-3
                border border-black rounded-l-md
                text-gray-700 text-sm
                placeholder-gray-400
                focus:outline-none focus:ring-2 focus:ring-blue-500
              "
            />
            <button
              onClick={() => {
                /* TODO: wire up AI‐submit logic with the input’s value */
              }}
              className="
                h-10
                px-4
                bg-black text-white
                font-medium text-sm
                rounded-r-md
                hover:bg-gray-800
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
                transition
              "
            >
              Send
            </button>
          </div>

          {/* ── RIGHT HALF: Buyer Buttons Row ───────────────────────────────────── */}
          <div className="flex space-x-2 overflow-x-auto">
            <button
              onClick={() => setTab('dealFlow')}
              className="px-3 py-1.5 border border-black rounded text-sm whitespace-nowrap"
            >
              Deal Flow
            </button>
            <button
              onClick={() => setTab('deliveries')}
              className="px-3 py-1.5 border border-black rounded text-sm whitespace-nowrap"
            >
              Shipments
            </button>
            <button
              onClick={() => setTab('notifications')}
              className="px-3 py-1.5 border border-black rounded text-sm whitespace-nowrap"
            >
              Messages
            </button>
            <button
              onClick={() => setTab('escrow')}
              className="px-3 py-1.5 border border-black rounded text-sm whitespace-nowrap"
            >
              Escrow
            </button>
            <button
              onClick={() => setTab('orders')}
              className="px-3 py-1.5 border border-black rounded text-sm whitespace-nowrap"
            >
              Contracts
            </button>
            <button
              onClick={() => setTab('supplierList')}
              className="px-3 py-1.5 border border-black rounded text-sm whitespace-nowrap"
            >
              Suppliers
            </button>
            <button
              onClick={() => setTab('products')}
              className="px-3 py-1.5 border border-black rounded text-sm whitespace-nowrap"
            >
              Products
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default BuyerDashboard