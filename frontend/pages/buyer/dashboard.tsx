// frontend/pages/buyer/dashboard.tsx
import { useEffect, useState } from 'react'
import { NextPage } from 'next'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import { ChartPoint } from '@/components/Chart'

// ----------------------------------------------------------------
// Buyer-specific metrics for the “Global Snapshot” section
// ----------------------------------------------------------------
const METRICS = [
  { key: 'totalSalesToday',    label: 'Sales Today',        colorClass: 'text-blue-600' },
  { key: 'openOrders',         label: 'Open Orders',        colorClass: 'text-green-600' },
  { key: 'pendingEscrow',      label: 'Pending Escrow',     colorClass: 'text-purple-600' },
  { key: 'availableProducts',  label: 'Available Products', colorClass: 'text-green-600' },
  { key: 'activeDeals',        label: 'Active Deals',       colorClass: 'text-blue-600' },
]

// ----------------------------------------------------------------
// Buyer dashboard buttons for the “Central Command” section
// ----------------------------------------------------------------
const COMMAND_BUTTONS = [
  'Deal Flow',
  'Shipments',
  'Messages',
  'Escrow',
  'Contracts',
  'Suppliers',
  'Products',
]

interface SupplierDashboardData {
  totalSalesToday: number
  openOrders: number
  pendingEscrow: number
  availableProducts: number
  activeDeals: number
  // (we’re not actually using real endpoints beyond metrics, so if you fetch
  // extra fields, feel free to add them here)
}

const BuyerDashboard: NextPage = () => {
  // 1) enforce login + buyer role
  useAuthRedirect('buyer')

  // 2) state for “global snapshot” data
  const [data, setData]       = useState<SupplierDashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  // 3) on‐mount: fetch whatever metrics endpoints exist
  useEffect(() => {
    let isMounted = true

    async function loadMetrics() {
      try {
        // -- Suppose we have an endpoint `/buyer/dashboard` returning the five metrics.
        const res = await api.get<SupplierDashboardData>('/buyer/dashboard')
        if (isMounted) {
          setData(res.data)
        }
      } catch (e) {
        console.warn('Failed to fetch buyer dashboard metrics; using zeros fallback.')
        if (isMounted) {
          // fallback to zeros if endpoint doesn’t exist
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

    loadMetrics()
    return () => {
      isMounted = false
    }
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

  // At this point `data` is guaranteed to be non-null
  const snapshot = data!

  return (
    <div className="min-h-screen bg-gray-50 relative">
      {/* ───────────────────────────────────────────────────────────────────────────── */}
      {/* Main content: Add pb-16 so we don’t hide behind the fixed terminal bar */}
      {/* ───────────────────────────────────────────────────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-5 pt-6 pb-16 space-y-6">
        {/* ── Global Snapshot + Central Command (two-column split) ─────────────────────────── */}
        <div className="bg-white border border-border-light dark:border-gray-700 rounded-lg overflow-hidden">
          <div className="grid grid-cols-1 md:grid-cols-2">
            {/* Left column: Text / Metrics / Buttons */}
            <div className="p-4 pr-6 border-r border-border-light dark:border-gray-700">
              {/* “Hello, Buyer — welcome to Central Command.” */}
              <p className="font-mono text-base text-gray-800 dark:text-text-secondary">
                Hello, Buyer — welcome to Central Command.
              </p>

              {/* Metrics lines */}
              <div className="mt-2 space-y-1 font-mono text-base text-gray-800 dark:text-text-secondary">
                {METRICS.map((m) => {
                  // compute the raw value from `snapshot`
                  const rawValue = (snapshot as any)[m.key] ?? 0
                  // prefix currency for “Available Products”? (if needed)
                  let display = rawValue
                  if (m.key === 'availableProducts') {
                    display = rawValue // or format if currency is needed
                  }
                  return (
                    <p key={m.key}>
                      <span>“{m.label}”: </span>
                      <span className={m.colorClass}>{display}</span>
                    </p>
                  )
                })}
              </div>

              {/* Divider between metrics and “instructions” */}
              <div className="border-t border-border-light dark:border-gray-700 mt-4 pt-2">
                <p className="italic text-sm text-gray-600 dark:text-text-secondary">
                  Select one of the buttons below, or type a question in the input bar.
                </p>
              </div>

              {/* Command buttons (left column) */}
              <div className="mt-2 space-x-2 space-y-2">
                {COMMAND_BUTTONS.map((label) => (
                  <button
                    key={label}
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

            {/* Right column: “Visual” placeholder */}
            <div className="p-4 pl-6 flex items-center justify-center">
              <p className="text-gray-500 dark:text-text-secondary">
                Select a button or ask a question to see visual output here.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* ───────────────────────────────────────────────────────────────────────────── */}
      {/* FIXED TERMINAL BAR (identical to supplier) */}
      {/* ───────────────────────────────────────────────────────────────────────────── */}
      <div
        className="
          fixed bottom-0 left-5 right-5      /* exactly 20px margin on left & right */
          bg-white
          border-t border-border-light dark:border-gray-700
          flex items-center
          h-12                              /* exactly 3rem tall */
          px-3
          space-x-2
          z-50
        "
      >
        {/* ── LEFT HALF: Input + Send button ───────────────────────────────────────── */}
        <div className="flex items-center space-x-2 flex-1">
          <input
            type="text"
            placeholder="Type a question (e.g. “Build my report”)"
            className="
              flex-1
              h-10
              px-3
              border border-black dark:border-gray-600 rounded-md
              text-gray-700 dark:text-text-secondary text-sm
              placeholder-gray-400 dark:placeholder-gray-500
              focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent
            "
          />
          <button
            className="
              h-10
              px-4
              bg-black text-white
              font-medium text-sm
              rounded-md
              hover:bg-gray-800
              focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-1
              transition
            "
          >
            Send
          </button>
        </div>

        {/* ── RIGHT HALF: Command Buttons (no scrollbar; wrap to next line if needed) ─────── */}
        <div className="flex items-center space-x-2 flex-shrink-0 flex-wrap">
          {COMMAND_BUTTONS.map((label) => (
            <button
              key={label}
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
  )
}

export default BuyerDashboard