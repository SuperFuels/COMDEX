// frontend/pages/supplier/dashboard.tsx

import { useEffect, useState, useRef } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import useSupplierDashboard from '@/hooks/useSupplierDashboard'
import Chart, { ChartPoint } from '@/components/Chart'

export default function SupplierDashboard() {
  // 1) Ensure only suppliers can view this page
  useAuthRedirect('supplier')

  // 2) Fetch supplier data
  const { data, loading, error } = useSupplierDashboard()

  // 3) Track which “tab” (Sales, Marketing, etc.) was clicked
  const [selectedTab, setSelectedTab] = useState<string>('')

  // 4) A ref in case we want to scroll the left pane later
  const leftPaneRef = useRef<HTMLDivElement>(null)

  // Loading or error states
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-page">
        <p className="text-text-secondary">Loading dashboard…</p>
      </div>
    )
  }
  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-page">
        <p className="text-red-600">{error || 'Unknown error'}</p>
      </div>
    )
  }

  // Prepare metrics for display
  const METRICS = [
    { key: 'totalSalesToday', label: 'Sales Today' },
    { key: 'activeListings',   label: 'Active Listings' },
    { key: 'openOrders',       label: 'Open Orders' },
    { key: 'proceeds30d',      label: '30d Proceeds' },
    { key: 'feedbackRating',   label: 'Feedback' },
  ]
  const metricsOutput = METRICS.map((m) => {
    const rawValue = (data as any)[m.key]
    if (m.key === 'proceeds30d') {
      return { label: m.label, value: `£${rawValue}`, color: 'text-blue-600' }
    }
    if (m.key === 'feedbackRating') {
      return { label: m.label, value: rawValue, color: 'text-purple-600' }
    }
    if (m.key === 'totalSalesToday') {
      return { label: m.label, value: rawValue, color: 'text-blue-600' }
    }
    // activeListings & openOrders → green
    return { label: m.label, value: rawValue, color: 'text-green-600' }
  })

  // Dummy 24-point time series for <Chart>
  const sampleChartData: ChartPoint[] = Array.from({ length: 24 }, (_, i) => ({
    time: Math.floor(Date.now() / 1000) - (23 - i) * 3600,
    value:
      (data.products.length > 0
        ? data.products[0].price_per_kg
        : 1) * 1000 +
      (Math.random() - 0.5) * 500,
  }))

  return (
    <div className="bg-bg-page min-h-screen flex flex-col">
      {/* ─── Spacer for sticky Navbar (height = 4rem) ────────────────── */}
      <div className="h-16" />

      {/* ─── Main “Text | Visual” Area ───────────────────────────────────── */}
      <main className="flex-1 max-w-[calc(100%-40px)] mx-auto px-2">
        <div className="flex h-[calc(100vh-4rem-4rem)]">
          {/* ── Left Pane: Text / “Terminal” ──────────────────────────── */}
          <div ref={leftPaneRef} className="flex-1 overflow-auto pr-2">
            <div className="h-full font-mono text-text dark:text-text-secondary text-sm">
              {/* Greeting + Metric Lines */}
              <p className="mb-2">Hello, Kevin — welcome to Central Command.</p>
              {metricsOutput.map((m) => (
                <p key={m.label} className="mb-1">
                  <span>{`“${m.label}”: `}</span>
                  <span className={`${m.color}`}>{m.value}</span>
                </p>
              ))}

              {/* AI Response / Instructions */}
              <div className="mt-4">
                {selectedTab === '' ? (
                  <p className="italic text-text-secondary">
                    Select one of the buttons below, or type a question in the input bar.
                  </p>
                ) : (
                  <div>
                    {/* Example dummy response for each tab */}
                    {selectedTab === 'Sales' && (
                      <>
                        <p className="mb-2">→ Here is your sales summary for today:</p>
                        <p className="mb-1">{`• “Sales Today”: ${ (data as any).totalSalesToday }`}</p>
                        <p className="mb-1">{`• “Active Listings”: ${ (data as any).activeListings }`}</p>
                        <p className="mb-1">{`• “Open Orders”: ${ (data as any).openOrders }`}</p>
                        <p className="mb-1">{`• “30d Proceeds”: £${ (data as any).proceeds30d }`}</p>
                        <p className="mb-1">{`• “Feedback”: ${ (data as any).feedbackRating }`}</p>
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

          {/* ── Vertical Divider ───────────────────────────────────────── */}
          <div className="w-px bg-border-light dark:bg-gray-700" />

          {/* ── Right Pane: Visual Output ───────────────────────────────── */}
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

      {/* ─── Fixed Bottom Bar ───────────────────────────────────────────── */}
      <footer className="fixed bottom-0 left-0 w-full bg-white dark:bg-gray-800 border-t border-border-light dark:border-gray-700 py-4">
        <div className="max-w-[calc(100%-40px)] mx-auto px-2">
          <div className="flex">
            {/* ── Left: Constrain to 50% − 20px so “Send” never crosses divider ───── */}
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
                  focus:outline-none focus:ring-2 focus:ring-blue-500
                "
              />
              <button
                className="
                  py-2 px-4
                  bg-black text-white
                  border border-black rounded
                  text-sm
                  hover:bg-gray-900
                  focus:outline-none focus:ring-2 focus:ring-blue-500
                  transition
                "
              >
                Send
              </button>
            </div>

            {/* ── Right: Shortcut Buttons (occupies remaining 50%) ─────────────────── */}
            <div className="w-[50%] flex justify-start space-x-2 pl-4">
              {['Sales', 'Marketing', 'Operations', 'Shipments', 'Financials', 'Clients'].map(
                (tab) => (
                  <button
                    key={tab}
                    onClick={() => setSelectedTab(tab)}
                    className={`
                      py-2 px-4 text-sm font-medium whitespace-nowrap
                      border border-black rounded
                      bg-white dark:bg-gray-900 text-black dark:text-white
                      hover:bg-gray-100 dark:hover:bg-gray-700
                      focus:outline-none
                    `}
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