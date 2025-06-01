// frontend/pages/supplier/dashboard.tsx
import { useEffect, useState } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import useSupplierDashboard from '@/hooks/useSupplierDashboard'
import Link from 'next/link'
import Chart, { ChartPoint } from '@/components/Chart' // reuse your existing Chart

const METRICS = [
  { key: 'totalSalesToday', label: 'Sales Today' },
  { key: 'activeListings',   label: 'Active Listings' },
  { key: 'openOrders',       label: 'Open Orders' },
  { key: 'proceeds30d',      label: '30d Proceeds' },
  { key: 'feedbackRating',   label: 'Feedback' },
]

// New tabs for “Manage Inventory”
const INVENTORY_TABS = [
  { key: 'sell',    label: 'Sell Product' },
  { key: 'edit',    label: 'Edit Product' },
  { key: 'active',  label: 'Active Products' },
  { key: 'messages',label: 'Messages' },
  { key: 'compliance', label: 'Compliance' },
  { key: 'reports', label: 'Reports' },
]

export default function SupplierDashboard() {
  // Redirect if not a supplier
  useAuthRedirect('supplier')

  // Fetch dashboard data
  const { data, loading, error } = useSupplierDashboard()
  const [selectedMetric, setSelectedMetric] = useState(METRICS[0].key)

  // State to track which Inventory tab is active:
  const [activeTab, setActiveTab] = useState<string>('sell')

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

  // Determine the current metric label + value
  const currentMetric = METRICS.find((m) => m.key === selectedMetric)!
  let rawValue = (data as any)[currentMetric.key]
  let displayValue: string | number = rawValue
  if (selectedMetric === 'proceeds30d') {
    displayValue = `£${rawValue}`
  }

  // Build some dummy chart data if you want to display something
  const sampleChartData: ChartPoint[] = Array.from({ length: 24 }, (_, i) => ({
    time:  Math.floor(Date.now() / 1000) - (23 - i) * 3600,
    value: (data.products.length > 0 ? data.products[0].price_per_kg : 1) * 1000 + (Math.random() - 0.5) * 500,
  }))

  return (
    <div className="bg-bg-page min-h-screen pb-8">
      <main className="max-w-7xl mx-auto px-4 pt-6 space-y-8">
        {/* ── Global Snapshot Container (full-width) ─────────────────────────────── */}
        <div className="bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg">
          <div className="p-4 flex flex-col md:flex-row md:items-center md:justify-between">
            <div className="flex items-center space-x-2">
              {/* Changed label here */}
              <label
                htmlFor="metricSelect"
                className="text-text-secondary font-medium"
              >
                Global Snapshot:
              </label>
              <select
                id="metricSelect"
                className="bg-white dark:bg-gray-800 border border-border-light dark:border-gray-600 rounded px-2 py-1 text-text text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                value={selectedMetric}
                onChange={(e) => setSelectedMetric(e.target.value)}
              >
                {METRICS.map((m) => (
                  <option key={m.key} value={m.key}>
                    {m.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="border-t border-border-light dark:border-gray-700 px-4 py-2 font-mono bg-white dark:bg-gray-800 text-text dark:text-text-secondary text-sm">
            <span className="font-mono">{currentMetric.label}:</span>{' '}
            <span
              className={`font-mono ${
                selectedMetric === 'feedbackRating'
                  ? 'text-purple-600'
                  : ['totalSalesToday', 'proceeds30d'].includes(selectedMetric)
                  ? 'text-blue-600'
                  : 'text-green-600'
              }`}
              style={{ fontWeight: 400 /* Not bold */ }}
            >
              {displayValue}
            </span>
          </div>
        </div>

        {/* ── Chart + AI Analysis Placeholders ─────────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* (A) Chart area */}
          <div className="bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg h-64 overflow-hidden">
            <Chart data={sampleChartData} height={256} />
          </div>

          {/* (B) AI Analysis area */}
          <div className="bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg h-64 p-4 overflow-auto font-sans text-black dark:text-text-secondary text-sm">
            <p className="mb-2">→ Fetching latest metrics…</p>
            <p className="mb-2">→ Analyzing sales trends for last 30 days…</p>
            <p className="mb-2">→ Generating insights…</p>
            <p className="mb-2">“Sales Today” shows a 5% uptick vs. yesterday.</p>
            <p className="mb-2">“30d Proceeds” have increased by £1,320.</p>
            <p className="mb-2">“Feedback Rating” stays steady at 4.7/5.</p>
            <p className="mb-2">[ More AI insights to come… ]</p>
          </div>
        </div>

        {/* ── “Manage Inventory” Tabbed Container ────────────────────────────────── */}
        <div className="bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg">
          {/* Header */}
          <div className="px-4 py-3 border-b border-border-light dark:border-gray-700">
            <h2 className="text-xl font-semibold text-text dark:text-text-secondary">
              Manage Inventory
            </h2>
          </div>

          {/* Tab Buttons */}
          <div className="px-4 pt-2">
            <nav className="flex space-x-4 overflow-x-auto">
              {INVENTORY_TABS.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`
                    py-2 px-4 text-sm font-medium
                    ${
                      activeTab === tab.key
                        ? 'border-b-2 border-black dark:border-white text-black dark:text-white'
                        : 'text-text-secondary dark:text-text-secondary'
                    }
                    focus:outline-none
                  `}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content Placeholder */}
          <div className="p-4">
            {activeTab === 'sell' && (
              <div>
                {/* TODO: Place your “Sell Product” form/component here */}
                <p className="text-text-secondary italic">
                  “Sell Product” tab content goes here.
                </p>
              </div>
            )}

            {activeTab === 'edit' && (
              <div>
                {/* TODO: Place your “Edit Product” form/component here */}
                <p className="text-text-secondary italic">
                  “Edit Product” tab content goes here.
                </p>
              </div>
            )}

            {activeTab === 'active' && (
              <div>
                {/* TODO: List of active products */}
                <p className="text-text-secondary italic">
                  “Active Products” list goes here.
                </p>
              </div>
            )}

            {activeTab === 'messages' && (
              <div>
                {/* TODO: Buyer Messages inbox/chat */}
                <p className="text-text-secondary italic">
                  “Messages” panel goes here.
                </p>
              </div>
            )}

            {activeTab === 'compliance' && (
              <div>
                {/* TODO: Compliance documents / checks */}
                <p className="text-text-secondary italic">
                  “Compliance” section goes here.
                </p>
              </div>
            )}

            {activeTab === 'reports' && (
              <div>
                {/* TODO: Reports / analytics */}
                <p className="text-text-secondary italic">
                  “Reports” section goes here.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}