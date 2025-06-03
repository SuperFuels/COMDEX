// frontend/pages/buyer/dashboard.tsx

import { useEffect, useState, useRef } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import Chart, { ChartPoint } from '@/components/Chart'

type SelectedTab = 
  | 'Deal Flow'
  | 'Shipments'
  | 'Messages'
  | 'Escrow'
  | 'Contracts'
  | 'Suppliers'
  | 'Products'
  | ''  // no tab selected

export default function BuyerDashboard() {
  // 1) enforce buyer role
  useAuthRedirect('buyer')

  // 2) local state for deals/products/chart
  const [deals, setDeals] = useState<any[]>([])
  const [products, setProducts] = useState<any[]>([])
  const [chartData, setChartData] = useState<ChartPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 3) which shortcut‐tab was clicked (e.g. “Deal Flow”, “Shipments”, etc.)
  const [selectedTab, setSelectedTab] = useState<SelectedTab>('')

  // 4) ref for left pane if needed in future
  const leftPaneRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    async function loadBuyerData() {
      try {
        // • Attempt to fetch “live” chart data (e.g. price_per_kg)
        let pts: ChartPoint[] = []
        try {
          const chartRes = await api.get<{ price_per_kg: number }[]>('/products')
          pts = chartRes.data.map(p => ({
            time: Math.floor(Date.now() / 1000),
            value: p.price_per_kg,
          }))
        } catch {
          console.warn('No chart endpoint; skipping.')
        }
        setChartData(pts)

        // • Fetch active deals
        try {
          const dealsRes = await api.get<any[]>('/deals')
          setDeals(dealsRes.data)
        } catch {
          console.warn('❌ Failed to fetch deals; continuing.')
        }

        // • Fetch marketplace listings (buyer sees available products)
        try {
          const prodRes = await api.get<any[]>('/products')
          setProducts(prodRes.data)
        } catch {
          console.warn('❌ Failed to fetch products; continuing.')
        }
      } catch (e) {
        console.error('❌ Error loading buyer data', e)
        setError('Failed to load buyer dashboard.')
      } finally {
        setLoading(false)
      }
    }
    loadBuyerData()
  }, [])

  // 5) loading / error states
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

  // 6) Prepare metrics (left‐pane)
  const METRICS = [
    { label: 'Sales Today',       value: 0,                        color: 'text-blue-600' }, 
    { label: 'Open Orders',       value: 0,                        color: 'text-green-600' },
    { label: 'Pending Escrow',    value: 0,                        color: 'text-purple-600' },
    { label: 'Available Products',value: products.length,          color: 'text-blue-600' },
    { label: 'Active Deals',      value: deals.length,             color: 'text-green-600' },
  ]

  // 7) Dummy 24-point series for right‐pane “Sales” chart
  const sampleChartData: ChartPoint[] = Array.from({ length: 24 }, (_, i) => ({
    time: Math.floor(Date.now() / 1000) - (23 - i) * 3600,
    value: chartData.length > 0 ? chartData[0].value : 0,
  }))

  return (
    <div className="bg-gray-50 min-h-screen flex flex-col">
      {/* ─── Spacer for sticky navbar (height = 4rem) ───────────────── */}
      <div className="h-16" />

      {/* ─── Main “Text | Visual” Area ───────────────────────────────────── */}
      <main className="flex-1 max-w-[calc(100%-0px)] mx-auto px-2">
        <div className="flex h-[calc(100vh-4rem-4rem)]">
          {/* ── Left Pane: Text/“Terminal” ─────────────────────────────── */}
          <div
            ref={leftPaneRef}
            className="flex-1 overflow-auto pr-2 bg-white border-r border-gray-200"
          >
            <div className="h-full font-mono text-gray-900 text-sm p-4">
              {/* Greeting + Metric Lines */}
              <p className="mb-2">Hello, Buyer — welcome to Central Command.</p>
              {METRICS.map(m => (
                <p key={m.label} className="mb-1">
                  <span>{`“${m.label}”: `}</span>
                  <span className={`${m.color} font-medium`}>{m.value}</span>
                </p>
              ))}

              {/* AI instructions / placeholder */}
              <div className="mt-4">
                {selectedTab === '' ? (
                  <p className="italic text-gray-500">
                    Select one of the buttons below, or type a question in the input bar.
                  </p>
                ) : (
                  <div>
                    {/* Example dummy response for each selectedTab */}
                    {selectedTab === 'Deal Flow' && (
                      <p>→ Fetching your active deals… (placeholder text)</p>
                    )}
                    {selectedTab === 'Shipments' && (
                      <p>→ Retrieving shipment statuses… (placeholder text)</p>
                    )}
                    {selectedTab === 'Messages' && (
                      <p>→ Opening your inbox… (placeholder text)</p>
                    )}
                    {selectedTab === 'Escrow' && (
                      <p>→ Checking pending escrow… (placeholder text)</p>
                    )}
                    {selectedTab === 'Contracts' && (
                      <p>→ Loading contracts… (placeholder text)</p>
                    )}
                    {selectedTab === 'Suppliers' && (
                      <p>→ Listing available suppliers… (placeholder text)</p>
                    )}
                    {selectedTab === 'Products' && (
                      <p>→ Displaying available products… (placeholder text)</p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ── Vertical Divider ───────────────────────────────────────── */}
          <div className="w-px bg-gray-200" />

          {/* ── Right Pane: Visual Output ───────────────────────────────── */}
          <div className="flex-1 overflow-auto pl-2 bg-white">
            {selectedTab === '' ? (
              <div className="h-full flex items-center justify-center text-gray-500">
                <p>Select a button or ask a question to see visual output here.</p>
              </div>
            ) : (
              <div className="h-full p-4">
                {selectedTab === 'Deal Flow' && (
                  <Chart data={sampleChartData} height={Math.floor(window.innerHeight - 4 * 16 - 64)} />
                )}
                {selectedTab !== 'Deal Flow' && (
                  <div className="h-full flex items-center justify-center">
                    <p className="italic text-gray-500">
                      [ Visual output for “{selectedTab}” would appear here ]
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ─── Fixed Bottom Terminal Bar ───────────────────────────────────── */}
      <footer className="fixed bottom-0 left-0 w-full bg-white border-t border-gray-200 py-4 z-50">
        <div className="max-w-[100%] mx-auto px-2">
          <div className="flex">
            {/* ── Left Side: Input + Send (exactly 50% minus 20px) ────────────── */}
            <div className="w-[calc(50%-20px)] flex items-center space-x-2">
              <input
                type="text"
                placeholder="Type a question (e.g. “Build my report”)"
                className="
                  flex-1
                  py-2 px-4
                  border border-black rounded
                  text-sm text-gray-700
                  placeholder-gray-400
                  focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                "
              />
              <button
                className="
                  py-2 px-4
                  bg-black text-white
                  border border-black rounded
                  text-sm font-medium
                  hover:bg-gray-800
                  focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
                  transition
                "
              >
                Send
              </button>
            </div>

            {/* ── Right Side: Shortcut Buttons ─────────────────────────────── */}
            <div className="w-[50%] flex items-center pl-4 space-x-2">
              {[
                'Deal Flow',
                'Shipments',
                'Messages',
                'Escrow',
                'Contracts',
                'Suppliers',
                'Products',
              ].map((tabName) => (
                <button
                  key={tabName}
                  onClick={() => setSelectedTab(tabName as SelectedTab)}
                  className="
                    py-2 px-4
                    border border-black rounded
                    bg-white text-black
                    text-sm font-medium whitespace-nowrap
                    hover:bg-gray-100
                    focus:outline-none
                  "
                >
                  {tabName}
                </button>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}