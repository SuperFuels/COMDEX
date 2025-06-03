// frontend/pages/buyer/dashboard.tsx
import React, { useEffect, useState } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import Chart, { ChartPoint } from '@/components/Chart'

interface BuyerMetrics {
  totalSalesToday: number
  openOrders: number
  pendingEscrow: number
  availableProducts: number
  activeDeals: number
}

const METRICS = [
  { key: 'totalSalesToday',   label: 'Sales Today',        color: 'text-blue-600' },
  { key: 'openOrders',        label: 'Open Orders',        color: 'text-green-600' },
  { key: 'pendingEscrow',     label: 'Pending Escrow',     color: 'text-purple-600' },
  { key: 'availableProducts', label: 'Available Products', color: 'text-green-600' },
  { key: 'activeDeals',       label: 'Active Deals',       color: 'text-blue-600' },
]

const COMMAND_TABS = [
  'Deal Flow',
  'Shipments',
  'Messages',
  'Escrow',
  'Contracts',
  'Suppliers',
  'Products',
]

export default function BuyerDashboard() {
  // 1) Only “buyer” can view this page
  useAuthRedirect('buyer')

  // 2) Fetch buyer‐specific metrics
  const [data, setData]       = useState<BuyerMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  // 3) Track which command tab is selected (for dummy textual “response”)
  const [selectedTab, setSelectedTab] = useState<string>('')

  // 4) Build a dummy chart time‐series (24 points) for the “Visual” pane if needed
  const [sampleChartData, setSampleChartData] = useState<ChartPoint[]>([])

  // 5) On‐mount: fetch metrics + build dummy chart series
  useEffect(() => {
    let isMounted = true

    async function fetchMetrics() {
      try {
        // Suppose endpoint `/buyer/dashboard` returns { totalSalesToday, openOrders, pendingEscrow, availableProducts, activeDeals }
        const res = await api.get<BuyerMetrics>('/buyer/dashboard')
        if (isMounted) {
          setData(res.data)
        }
      } catch {
        console.warn('Failed to fetch buyer metrics; using zeros fallback.')
        if (isMounted) {
          setData({
            totalSalesToday: 0,
            openOrders: 0,
            pendingEscrow: 0,
            availableProducts: 0,
            activeDeals: 0,
          })
        }
      } finally {
        if (isMounted) setLoading(false)
      }
    }

    // Build a dummy 24-point chart (e.g. for “Deal Flow”)
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

  // 6) Display loading / error states if needed
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

  // Data is now non‐null
  const metrics = data!

  return (
    <div className="bg-gray-50 min-h-screen flex flex-col">
      {/* ─── Spacer for Sticky Navbar (height = 4rem) ──────────────── */}
      <div className="h-16" />

      {/* ─── Main “Text | Visual” Area ─────────────────────────────── */}
      <main className="flex-1 max-w-[calc(100%-40px)] mx-auto px-2">
        <div className="flex h-[calc(100vh-4rem-4rem)]">
          {/* ── Left Pane: Greeting, Metrics & Command Buttons ────────── */}
          <div className="flex-1 overflow-y-auto pr-2">
            <div className="h-full font-mono text-gray-800 dark:text-gray-200 text-sm">
              {/* Greeting */}
              <p className="mb-2">Hello, Buyer — welcome to Central Command.</p>

              {/* Metrics */}
              <div className="space-y-1">
                {METRICS.map((m) => {
                  const raw = (metrics as any)[m.key] ?? 0
                  return (
                    <p key={m.key}>
                      <span>“{m.label}”: </span>
                      <span className={m.color}>{raw}</span>
                    </p>
                  )
                })}
              </div>

              {/* Divider + Instructions */}
              <div className="border-t border-gray-300 dark:border-gray-700 mt-4 pt-2">
                <p className="italic text-sm text-gray-600 dark:text-gray-400">
                  Select one of the buttons below, or type a question in the input bar.
                </p>
              </div>

              {/* Command Buttons */}
              <div className="mt-2 flex flex-wrap space-x-2">
                {COMMAND_TABS.map((label) => (
                  <button
                    key={label}
                    onClick={() => setSelectedTab(label)}
                    className="
                      px-3 py-1
                      border border-black dark:border-gray-600
                      rounded-md
                      text-sm text-black dark:text-white
                      hover:bg-gray-100 dark:hover:bg-gray-700
                      focus:outline-none
                    "
                  >
                    {label}
                  </button>
                ))}
              </div>

              {/* Dummy textual “response” section (when a tab is selected) */}
              {selectedTab !== '' && (
                <div className="mt-4 space-y-2">
                  {selectedTab === 'Deal Flow' && (
                    <>
                      <p>→ Here is a summary of your deals:</p>
                      <p className="pl-2">• You currently have {metrics.activeDeals} active deals.</p>
                    </>
                  )}
                  {selectedTab === 'Shipments' && (
                    <p>→ Retrieving shipment statuses… (placeholder text)</p>
                  )}
                  {selectedTab === 'Messages' && (
                    <p>→ Opening message inbox… (placeholder text)</p>
                  )}
                  {selectedTab === 'Escrow' && (
                    <p>→ Showing your pending escrow balance: {metrics.pendingEscrow}</p>
                  )}
                  {selectedTab === 'Contracts' && (
                    <p>→ Fetching contract list… (placeholder text)</p>
                  )}
                  {selectedTab === 'Suppliers' && (
                    <p>→ Listing your suppliers… (placeholder text)</p>
                  )}
                  {selectedTab === 'Products' && (
                    <p>→ Showing available products: {metrics.availableProducts}</p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* ── Vertical Divider ─────────────────────────────────────── */}
          <div className="w-px bg-gray-300 dark:bg-gray-700" />

          {/* ── Right Pane: Visual Output ─────────────────────────────── */}
          <div className="flex-1 overflow-y-auto pl-2">
            {selectedTab === '' ? (
              <div className="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
                <p>Select a button or ask a question to see visual output here.</p>
              </div>
            ) : (
              <div className="h-full">
                {selectedTab === 'Deal Flow' ? (
                  <Chart
                    data={sampleChartData}
                    // Height = 100vh − 4rem (navbar) − 4rem (footer)
                    height={Math.floor(window.innerHeight - 4 * 16 - 64)}
                  />
                ) : (
                  <div className="h-full flex items-center justify-center">
                    <p className="italic text-gray-500 dark:text-gray-400">
                      [Visual output for “{selectedTab}” will appear here.]
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ─── Fixed Bottom “Terminal” Bar ─────────────────────────────── */}
      <footer className="fixed bottom-0 left-0 w-full bg-white dark:bg-gray-800 border-t border-gray-300 dark:border-gray-700 py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-2">
          <div className="flex">
            {/* ── Left Half: Input + Send ──────────────────────────────── */}
            <div className="w-[calc(50%-20px)] flex items-center space-x-2">
              <input
                type="text"
                placeholder="Type a question (e.g. “Build my report”)"
                className="
                  flex-1
                  py-2 px-4
                  border border-black dark:border-gray-600 rounded
                  bg-white dark:bg-gray-900
                  text-sm text-black dark:text-gray-200
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

            {/* ── Right Half: Buyer Command Buttons ───────────────────── */}
            <div className="w-[50%] flex flex-wrap items-center space-x-2 pl-4">
              {COMMAND_TABS.map((label) => (
                <button
                  key={label}
                  onClick={() => setSelectedTab(label)}
                  className="
                    px-3 py-1
                    border border-black dark:border-gray-600
                    rounded-md
                    text-sm text-black dark:text-white
                    hover:bg-gray-100 dark:hover:bg-gray-700
                    focus:outline-none
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