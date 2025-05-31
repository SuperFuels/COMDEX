// frontend/pages/supplier/dashboard.tsx

import { useEffect, useState } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import useSupplierDashboard from '@/hooks/useSupplierDashboard'
import Link from 'next/link'

const METRICS = [
  { key: 'totalSalesToday', label: 'Sales Today' },
  { key: 'activeListings',   label: 'Active Listings' },
  { key: 'openOrders',       label: 'Open Orders' },
  { key: 'proceeds30d',      label: '30d Proceeds' },
  { key: 'feedbackRating',   label: 'Feedback' },
]

export default function SupplierDashboard() {
  useAuthRedirect('supplier')
  const { data, loading, error } = useSupplierDashboard()
  const [selectedMetric, setSelectedMetric] = useState(METRICS[0].key)

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

  // Find the selected metric’s label/value
  const currentMetric = METRICS.find((m) => m.key === selectedMetric)!
  let rawValue = (data as any)[currentMetric.key]
  let displayValue: string | number = rawValue

  if (selectedMetric === 'proceeds30d') {
    displayValue = `£${rawValue}`
  }

  return (
    <div className="bg-bg-page min-h-screen pb-8">
      <main className="max-w-7xl mx-auto px-4 pt-6 space-y-8">
        {/* ── Terminal‐Style Metric Container (FULL WIDTH) ─────────────── */}
        <div className="bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg">
          <div className="p-4 flex flex-col md:flex-row md:items-center md:justify-between">
            <div className="flex items-center space-x-2">
              <label
                htmlFor="metricSelect"
                className="text-text-secondary font-medium"
              >
                Metric:
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
                  : ['totalSalesToday', 'proceeds30d'].includes(
                      selectedMetric
                    )
                  ? 'text-blue-600'
                  : 'text-green-600'
              }`}
              style={{ fontWeight: 400 /* Not bold */ }}
            >
              {displayValue}
            </span>
          </div>
        </div>

        {/* ── Chart Placeholders (two columns, responsive) ───────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg h-64 flex items-center justify-center text-text-secondary">
            Chart placeholder
          </div>
          <div className="bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg h-64 flex items-center justify-center text-text-secondary">
            AI Analysis placeholder
          </div>
        </div>

        {/* ── “My Listings” Table ───────────────────────────────────────────────── */}
        <div className="bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-text mb-2">
            My Listings
          </h2>
          {data.products.length === 0 ? (
            <p className="text-text-secondary">You have no active listings yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full table-auto">
                <thead className="bg-gray-100 dark:bg-gray-700">
                  <tr>
                    <th className="px-4 py-2 text-left text-text-secondary">
                      Title
                    </th>
                    <th className="px-4 py-2 text-left text-text-secondary">
                      Category
                    </th>
                    <th className="px-4 py-2 text-left text-text-secondary">
                      Origin
                    </th>
                    <th className="px-4 py-2 text-right text-text-secondary">
                      Price / kg
                    </th>
                    <th className="px-4 py-2 text-right text-text-secondary">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.products.map((p) => (
                    <tr
                      key={p.id}
                      className="border-t border-border-light dark:border-gray-700"
                    >
                      <td className="px-4 py-2">{p.title}</td>
                      <td className="px-4 py-2">{p.category}</td>
                      <td className="px-4 py-2">{p.origin_country}</td>
                      <td className="px-4 py-2 text-right">
                        £{p.price_per_kg.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        <Link href={`/products/edit/${p.id}`} prefetch={false}>
                          <a className="text-primary hover:underline text-sm">
                            Edit
                          </a>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* ── Sell Product CTA ──────────────────────────────────────────────────── */}
        <div className="text-right">
          <Link href="/products/new" prefetch={false}>
            <a className="btn-filled">+ Sell Product</a>
          </Link>
        </div>
      </main>
    </div>
  )
}