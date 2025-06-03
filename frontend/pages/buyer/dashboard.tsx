// frontend/pages/buyer/dashboard.tsx
import { useEffect, useState } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import Chart, { ChartPoint } from '@/components/Chart'

/** Shape of the metrics returned by /buyer/dashboard (or fallback). */
interface BuyerMetrics {
  totalSalesToday: number
  openOrders: number
  pendingEscrow: number
  availableProducts: number
  activeDeals: number
}

/** How we display each metric in the left pane. */
const METRICS = [
  { key: 'totalSalesToday',   label: 'Sales Today',        color: 'text-blue-600' },
  { key: 'openOrders',        label: 'Open Orders',        color: 'text-green-600' },
  { key: 'pendingEscrow',     label: 'Pending Escrow',     color: 'text-purple-600' },
  { key: 'availableProducts', label: 'Available Products', color: 'text-green-600' },
  { key: 'activeDeals',       label: 'Active Deals',       color: 'text-blue-600' },
]

export default function BuyerDashboard() {
  // ─── 1) Only “buyer” can view this page ─────────────────────────────────
  useAuthRedirect('buyer')

  // ─── 2) Fetch buyer‐specific metrics (and track loading / error) ─────────
  const [metrics, setMetrics]   = useState<BuyerMetrics | null>(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState<string | null>(null)

  // ─── 3) Track which “bottom” button is clicked (for visual pane) ──────────
  const [selectedTab, setSelectedTab] = useState<string>('')

  // ─── 4) Build a dummy 24‐point chart time‐series for “Deal Flow” visual ──
  const [sampleChartData, setSampleChartData] = useState<ChartPoint[]>([])

  // ─── 5) On‐mount: fetch metrics + prepare dummy chart points ───────────────
  useEffect(() => {
    let isMounted = true

    async function fetchMetrics() {
      try {
        // Example: GET /buyer/dashboard returns { totalSalesToday, openOrders, pendingEscrow, availableProducts, activeDeals }
        const res = await api.get<BuyerMetrics>('/buyer/dashboard')
        if (isMounted) {
          setMetrics(res.data)
        }
      } catch {
        console.warn('Failed to fetch buyer metrics; using zeros fallback.')
        if (isMounted) {
          setMetrics({
            totalSalesToday:     0,
            openOrders:          0,
            pendingEscrow:       0,
            availableProducts:   0,
            activeDeals:         0,
          })
        }
      } finally {
        if (isMounted) setLoading(false)
      }
    }

    // Build dummy 24‐point chart for “Deal Flow”
    const pts: ChartPoint[] = Array.from({ length: 24 }, (_, i) => ({
      time:  Math.floor(Date.now() / 1000) - (23 - i) * 3600,
      value: 1000 + (Math.random() - 0.5) * 500,
    }))
    setSampleChartData(pts)

    fetchMetrics()
    return () => {
      isMounted = false
    }
  }, [])

  // ─── 6) Loading / error states ─────────────────────────────────────────────
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

  // By this point, metrics is guaranteed non‐null
  const data = metrics!

  // ─── 7) Render the page ────────────────────────────────────────────────────
  return (
    <div className="bg-gray-50 min-h-screen flex flex-col">
      {/* ─── Spacer for Sticky Navbar (height = 4rem) ─────────────────────────── */}
      <div className="h-16" />

      {/* ─── Main “Text | Visual” Area ────────────────────────────────────────── */}
      <main className="flex-1 max-w-[calc(100%-40px)] mx-auto px-2">
        <div className="flex h-[calc(100vh-4rem-4rem)]">
          {/* ── Left Pane: Buyer Greeting + Metrics (no buttons here) ──────────── */}
          <div className="flex-1 overflow-y-auto pr-2">
            <div className="h-full font-mono text-gray-800 dark:text-gray-200 text-sm">
              {/* Greeting */}
              <p className="mb-2">Hello, Buyer — welcome to Central Command.</p>

              {/* Metrics */}
              <div className="space-y-1">
                {METRICS.map((m) => {
                  const raw = (data as any)[m.key] ?? 0
                  return (
                    <p key={m.key}>
                      <span>“{m.label}”: </span>
                      <span className={m.color}>{raw}</span>
                    </p>
                  )
                })}
              </div>

              {/* 
                ─── NOTE ───
                We have REMOVED the “Select one of the buttons below, or type a question…”
                line and the COMMAND_TABS buttons from this left pane entirely.
              */}
            </div>
          </div>

          {/* ── Vertical Divider ───────────────────────────────────────────── */}
          <div className="w-px bg-gray-300 dark:bg-gray-700" />

          {/* ── Right Pane: Visual Output ─────────────────────────────────────── */}
          <div className="flex-1 overflow-y-auto pl-2">
            {selectedTab === 'Deal Flow' ? (
              <Chart
                data={sampleChartData}
                // height = viewport height minus top navbar (4rem) minus bottom bar (4rem)
                height={window.innerHeight - 4 * 16 - 64}
              />
            ) : (
              <div className="h-full flex items-center justify-center">
                <p className="italic text-gray-500 dark:text-gray-400">
                  Select a button or ask a question to see visual output here.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ─── Fixed Bottom “Terminal” Bar ───────────────────────────────────── */}
      <footer className="fixed bottom-0 left-0 w-full bg-white dark:bg-gray-800 border-t border-gray-300 dark:border-gray-700 py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-2">
          <div className="flex">
            {/* ── Left Half: Input + Send (50% width minus 20px) ──────────────────── */}
            <div className="w-[calc(50%-20px)] flex items-center space-x-2">
              <input
                type="text"
                placeholder="Type a question (e.g. “Build my sales report”)"
                className="
                  flex-1
                  py-2 px-4
                  border border-black dark:border-gray-600 rounded
                  bg-white dark:bg-gray-900
                  text-sm text-gray-800 dark:text-gray-200
                  placeholder-gray-400 dark:placeholder-gray-500
                  focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                "
              />
              <button
                className="
                  py-2 px-4
                  bg-black text-white
                  border border-black
                  rounded
                  text-sm
                  hover:bg-gray-900
                  focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
                  transition
                "
              >
                Send
              </button>
            </div>

            {/* ── Right Half: Bottom Command Buttons ──────────────────────────────── */}
            <div className="w-[50%] flex flex-wrap items-center space-x-2 pl-4">
              {[
                'Deal Flow',
                'Shipments',
                'Messages',
                'Escrow',
                'Contracts',
                'Suppliers',
                'Products',
              ].map((label) => (
                <button
                  key={label}
                  onClick={() => setSelectedTab(label)}
                  className="
                    px-3 py-1
                    border border-black dark:border-gray-600
                    rounded-md
                    text-sm text-gray-800 dark:text-gray-200
                    hover:bg-gray-100 dark:hover:bg-gray-700
                    focus:outline-none
                    transition
                  "
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}