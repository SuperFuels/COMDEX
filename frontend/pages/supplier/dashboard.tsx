// frontend/pages/supplier/dashboard.tsx

import { useState } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import useSupplierDashboard from '@/hooks/useSupplierDashboard'
import Chart, { ChartPoint } from '@/components/Chart'

// ----------------------------------------------------------------
// Metrics used at the top
// ----------------------------------------------------------------
const METRICS = [
  { key: 'totalSalesToday', label: 'Sales Today' },
  { key: 'activeListings',   label: 'Active Listings' },
  { key: 'openOrders',       label: 'Open Orders' },
  { key: 'proceeds30d',      label: '30d Proceeds' },
  { key: 'feedbackRating',   label: 'Feedback' },
]

// ----------------------------------------------------------------
// Main SupplierDashboard component
// ----------------------------------------------------------------
export default function SupplierDashboard() {
  // 1) If user is not a supplier, they will be redirected
  useAuthRedirect('supplier')

  // 2) Fetch supplier-specific data
  const { data, loading, error } = useSupplierDashboard()

  // 3) AI terminal input state
  const [aiInput, setAiInput] = useState('')

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

  // Map each metric to a {label, value, color}
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
    // activeListings & openOrders
    return { label: m.label, value: rawValue, color: 'text-green-600' }
  })

  // A dummy 24-point time series for the “Sales” chart
  const sampleChartData: ChartPoint[] = Array.from({ length: 24 }, (_, i) => ({
    time: Math.floor(Date.now() / 1000) - (23 - i) * 3600,
    value:
      (data.products.length > 0 ? data.products[0].price_per_kg : 1) * 1000 +
      (Math.random() - 0.5) * 500,
  }))

  return (
    <div className="bg-bg-page min-h-screen">
      <main className="max-w-7xl mx-auto px-4 pt-5 space-y-8">

        {/* ─── AI “Central Command” Terminal (Text | Visual) ───────────────────────── */}
        <div className="bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg overflow-hidden">
          {/* (1) Side-by-side panes */}
          <div className="flex border-b border-border-light dark:border-gray-700">
            {/* Left: Text Conversation + Metrics */}
            <div className="w-1/2 h-96 p-6 overflow-auto font-mono text-lg text-text dark:text-text-secondary space-y-4">
              {/* Inject metrics at top */}
              <div className="space-y-1">
                <p className="text-gray-600 dark:text-gray-400">
                  Hello, Kevin — welcome to Central Command.
                </p>
                {metricsOutput.map((m) => (
                  <p key={m.label}>
                    <span>{`“${m.label}”: `}</span>
                    <span className={m.color}>{m.value}</span>
                  </p>
                ))}
              </div>

              {/* Placeholder for AI’s dynamic response */}
              <div className="mt-4">
                <p>[…] AI response will appear here […]</p>
              </div>
            </div>

            {/* Right: Dummy “Sales” Chart */}
            <div className="w-1/2 h-96 p-6 bg-gray-100 dark:bg-gray-900 flex items-center justify-center">
              <Chart data={sampleChartData} height={320} />
            </div>
          </div>

          {/* (2) Buttons + Input at bottom */}
          <div className="px-6 pt-6 pb-6 bg-gray-50 dark:bg-gray-900">
            {/* Horizontal Buttons */}
            <div className="flex flex-wrap gap-2 mb-6">
              {['Sales', 'Marketing', 'Operations', 'Shipments', 'Financials', 'Clients'].map((btn) => (
                <button
                  key={btn}
                  onClick={() => {
                    // TODO: trigger AI fetch for “btn” category
                  }}
                  className="
                    px-3 py-1
                    bg-white dark:bg-gray-800
                    border border-black
                    rounded-md
                    text-sm text-text dark:text-text-secondary
                    hover:bg-gray-100 dark:hover:bg-gray-700
                    focus:outline-none
                  "
                >
                  {btn}
                </button>
              ))}
            </div>

            {/* Single Input + Send Button */}
            <div className="flex items-center space-x-3">
              <input
                type="text"
                value={aiInput}
                onChange={(e) => setAiInput(e.target.value)}
                placeholder="Type a question (e.g. build my sales report), or click a button"
                className="
                  flex-1
                  px-4 py-4
                  bg-white dark:bg-gray-800
                  border border-black
                  rounded-lg
                  text-lg text-text dark:text-text-secondary
                  placeholder-gray-400 dark:placeholder-gray-500
                  focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                "
              />
              <button
                onClick={() => {
                  // TODO: trigger AI send logic
                }}
                className="
                  px-5 py-4
                  bg-white dark:bg-gray-800
                  border border-black
                  rounded-lg
                  hover:bg-gray-100 dark:hover:bg-gray-700
                  focus:outline-none
                "
                aria-label="Send message"
              >
                Send
              </button>
            </div>
          </div>
        </div>
        {/* ────────────────────────────────────────────────────────────────────────── */}

        {/* ── “Manage Inventory” has been removed from this page ────────────────────── */}
        {/* You can link to a new “Manage Inventory” page via the sidebar. */}

      </main>
    </div>
  )
}