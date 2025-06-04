// File: frontend/pages/supplier/dashboard.tsx

import { useEffect, useState, useRef } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import Chart, { ChartPoint } from '@/components/Chart'
import api from '@/lib/api'

type SupplierData = {
  totalSalesToday: number
  activeListings: number
  openOrders: number
  proceeds30d: number
  feedbackRating: number
  products: {
    id: number
    title: string
    description: string
    price_per_kg: number
    origin_country: string
    image_url: string
  }[]
}

export default function SupplierDashboard() {
  // 1) Ensure only suppliers can view this page
  useAuthRedirect('supplier')

  // 2) Local state for supplier data, loading, error
  const [data, setData] = useState<SupplierData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 3) Track which tab was clicked
  const [selectedTab, setSelectedTab] = useState<string>('')

  // 4) A ref for scrolling the left pane if needed
  const leftPaneRef = useRef<HTMLDivElement>(null)

  // 5) On‐mount: fetch supplier data from Cloud Run via NEXT_PUBLIC_API_URL
  useEffect(() => {
    let isMounted = true

    async function fetchDashboard() {
      try {
        // Build the full Cloud Run endpoint
        const endpoint = `${process.env.NEXT_PUBLIC_API_URL}/supplier/dashboard`
        const resp = await api.get<SupplierData>(endpoint)
        if (isMounted) {
          setData(resp.data)
        }
      } catch (err: any) {
        console.error('[SupplierDashboard] fetch failed:', err)
        if (isMounted) {
          setError(err.message || 'Error fetching supplier data')
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    fetchDashboard()
    return () => {
      isMounted = false
    }
  }, [])

  // 6) Show loading / error states
  if (loading || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-page">
        <p className="text-text-secondary">Loading dashboard…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-page">
        <p className="text-red-600">{error}</p>
      </div>
    )
  }

  // 7) At this point, data is non‐null
  //    Extract metrics + products
  const metricsOutput = [
    {
      label: 'Sales Today',
      value: data.totalSalesToday,
      color: 'text-blue-600',
    },
    {
      label: 'Active Listings',
      value: data.activeListings,
      color: 'text-green-600',
    },
    {
      label: 'Open Orders',
      value: data.openOrders,
      color: 'text-green-600',
    },
    {
      label: '30d Proceeds',
      value: `£${data.proceeds30d}`,
      color: 'text-blue-600',
    },
    {
      label: 'Feedback',
      value: data.feedbackRating,
      color: 'text-purple-600',
    },
  ]

  // 8) Dummy 24‐point time series for the “Sales” chart
  const sampleChartData: ChartPoint[] = Array.from({ length: 24 }, (_ , i) => ({
    time: Math.floor(Date.now() / 1000) - (23 - i) * 3600,
    value:
      (data.products.length > 0
        ? data.products[0].price_per_kg
        : 1) * 1000 + (Math.random() - 0.5) * 500,
  }))

  return (
    <div className="bg-bg-page min-h-screen flex flex-col">
      {/* Spacer for sticky Navbar (height = 4rem) */}
      <div className="h-16" />

      {/* Main “Text | Visual” area */}
      <main className="flex-1 max-w-[calc(100%-40px)] mx-auto px-2">
        <div className="flex h-[calc(100vh-4rem-4rem)]">
          {/* ── Left Pane: Text / Terminal ──────────────────────── */}
          <div ref={leftPaneRef} className="flex-1 overflow-auto pr-2">
            <div className="h-full font-mono text-text dark:text-text-secondary text-sm">
              {/* Greeting + Metrics */}
              <p className="mb-2">Hello, Supplier — welcome to Central Command.</p>
              {metricsOutput.map((m) => (
                <p key={m.label} className="mb-1">
                  <span>{`“${m.label}”: `}</span>
                  <span className={m.color}>{m.value}</span>
                </p>
              ))}

              {/* AI / Instructional Text */}
              <div className="mt-4">
                {selectedTab === '' ? (
                  <p className="italic text-text-secondary">
                    Select one of the buttons below, or type a question in the input bar.
                  </p>
                ) : (
                  <div>
                    {selectedTab === 'Sales' && (
                      <>
                        <p className="mb-2">→ Here is your sales summary for today:</p>
                        <p className="mb-1">{`• “Sales Today”: ${data.totalSalesToday}`}</p>
                        <p className="mb-1">{`• “Active Listings”: ${data.activeListings}`}</p>
                        <p className="mb-1">{`• “Open Orders”: ${data.openOrders}`}</p>
                        <p className="mb-1">{`• “30d Proceeds”: £${data.proceeds30d}`}</p>
                        <p className="mb-1">{`• “Feedback”: ${data.feedbackRating}`}</p>
                      </>
                    )}
                    {selectedTab === 'Marketing' && (
                      <p>→ Generating your marketing plan… (placeholder text)</p>
                    )}
                    {selectedTab === 'Operations' && (
                      <p>→ Fetching operations metrics… (placeholder text)</p>
                    )}
                    {selectedTab === 'Shipments' && (
                      <p>→ Retrieving shipment statuses… (placeholder text)</p>
                    )}
                    {selectedTab === 'Financials' && (
                      <p>→ Compiling financial report… (placeholder text)</p>
                    )}
                    {selectedTab === 'Clients' && (
                      <p>→ Listing top clients… (placeholder text)</p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* ── Vertical Divider ───────────────────────────────────── */}
          <div className="w-px bg-border-light dark:bg-gray-700" />

          {/* ── Right Pane: Visual Output ─────────────────────────── */}
          <div className="flex-1 overflow-auto pl-2">
            {selectedTab === '' ? (
              <div className="h-full flex items-center justify-center text-text-secondary">
                <p>Select a button or ask a question to see visual output here.</p>
              </div>
            ) : (
              <div className="h-full">
                {selectedTab === 'Sales' && (
                  <Chart
                    data={sampleChartData}
                    height={Math.floor(window.innerHeight - 4 * 16 - 64)}
                  />
                )}
                {selectedTab !== 'Sales' && (
                  <div className="h-full flex items-center justify-center">
                    <p className="text-text-secondary italic">
                      [ Visual output for “{selectedTab}” would appear here ]
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ─── Fixed Bottom Bar ───────────────────────────────────── */}
      <footer className="fixed bottom-0 left-0 w-full bg-white dark:bg-gray-800 border-t border-border-light dark:border-gray-700 py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-2">
          <div className="flex">
            {/* LEFT: Constrain to 50% - 20px so “Send” never crosses divider */}
            <div className="w-[calc(50%-20px)] flex items-center space-x-2">
              <input
                type="text"
                placeholder="Type a question (e.g. “Build my sales report”)"
                className="
                  flex-1
                  py-2 px-4
                  border border-black rounded
                  bg-white dark:bg-gray-900
                  text-sm text-text dark:text-text-secondary
                  focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                "
                disabled
              />
              <button
                className="
                  py-2 px-4
                  bg-black text-white
                  border border-black rounded
                  text-sm
                  hover:bg-gray-900
                  focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
                  transition
                "
                disabled
              >
                Send
              </button>
            </div>

            {/* RIGHT: Shortcut Buttons (remaining 50%) */}
            <div className="w-[50%] flex justify-start space-x-2 pl-4">
              {['Sales', 'Marketing', 'Operations', 'Shipments', 'Financials', 'Clients'].map(
                (tab) => (
                  <button
                    key={tab}
                    onClick={() => setSelectedTab(tab)}
                    className="
                      py-2 px-4
                      text-sm font-medium whitespace-nowrap
                      border border-black rounded
                      bg-white dark:bg-gray-900 text-black dark:text-white
                      hover:bg-gray-100 dark:hover:bg-gray-700
                      focus:outline-none
                    "
                  >
                    {tab}
                  </button>
                )
              )}
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}