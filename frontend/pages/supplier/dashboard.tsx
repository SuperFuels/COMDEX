// frontend/pages/supplier/dashboard.tsx
import { useState, useEffect } from 'react'
import Link from 'next/link'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import useSupplierDashboard from '@/hooks/useSupplierDashboard'

type MetricKey =
  | 'Sales Today'
  | 'Active Listings'
  | 'Open Orders'
  | '30d Proceeds'
  | 'Feedback'

interface MetricInfo {
  label: MetricKey
  // actual value can be number or string (e.g. "£123")
  value: number | string
  // text color for highlighting (Tailwind classes)
  colorClass: string
}

export default function SupplierDashboard() {
  // Only suppliers allowed here
  useAuthRedirect('supplier')

  const { data, loading, error } = useSupplierDashboard()

  // Local state: which metric is currently selected
  const [selectedMetric, setSelectedMetric] = useState<MetricKey>('Sales Today')
  // Metric list for the <select>
  const metricOptions: MetricKey[] = [
    'Sales Today',
    'Active Listings',
    'Open Orders',
    '30d Proceeds',
    'Feedback',
  ]

  // Build a map of MetricKey → MetricInfo (with proper coloring)
  const metricMap: Record<MetricKey, MetricInfo> = {
    'Sales Today': {
      label: 'Sales Today',
      value: data ? data.totalSalesToday : 0,
      colorClass: 'text-blue-600',
    },
    'Active Listings': {
      label: 'Active Listings',
      value: data ? data.activeListings : 0,
      colorClass: 'text-green-600',
    },
    'Open Orders': {
      label: 'Open Orders',
      value: data ? data.openOrders : 0,
      colorClass: 'text-red-600',
    },
    '30d Proceeds': {
      label: '30d Proceeds',
      // data.proceeds30d already includes the "£" in useSupplierDashboard
      value: data ? `£${data.proceeds30d}` : '£0',
      colorClass: 'text-purple-600',
    },
    Feedback: {
      label: 'Feedback',
      value: data ? data.feedbackRating : 0,
      colorClass: 'text-yellow-500',
    },
  }

  // If still loading, show a full‐page spinner
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-600">Loading dashboard…</p>
      </div>
    )
  }

  // If there was an error or no data, show a full‐page message
  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-red-600">{error || 'Unknown error'}</p>
      </div>
    )
  }

  // Grab the currently selected metric info
  const currentMetric = metricMap[selectedMetric]

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="p-6 max-w-3xl mx-auto">
        {/* ─── Single “ChatGPT-style” Container ────────────────────────────────────── */}
        <div className="bg-white border border-gray-200 rounded-lg shadow p-6">
          {/* Drop-down to choose which metric to view */}
          <div className="flex items-center mb-4">
            <label
              htmlFor="metric-select"
              className="mr-2 text-gray-700 font-medium"
            >
              Metric:
            </label>
            <select
              id="metric-select"
              value={selectedMetric}
              onChange={(e) =>
                setSelectedMetric(e.target.value as MetricKey)
              }
              className="border border-gray-300 rounded px-3 py-1 font-sans text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {metricOptions.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>

          {/* Code‐looking output block (monospace, tinted background) */}
          <pre className="bg-gray-100 rounded p-4 font-mono text-base overflow-x-auto">
            <code className="block whitespace-pre-wrap">
              <span className="text-gray-800">
                {currentMetric.label}:
              </span>{' '}
              <span className={`${currentMetric.colorClass} font-semibold`}>
                {currentMetric.value}
              </span>
            </code>
          </pre>
        </div>

        {/* ─── Existing “My Listings” Table Below ───────────────────────────────── */}
        <div className="mt-8 bg-white border border-gray-200 rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-4">My Listings</h2>
          {data.products.length === 0 ? (
            <p className="text-gray-500">You have no active listings yet.</p>
          ) : (
            <table className="min-w-full table-auto">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left">Title</th>
                  <th className="px-4 py-2 text-left">Category</th>
                  <th className="px-4 py-2 text-left">Origin</th>
                  <th className="px-4 py-2 text-right">Price / kg</th>
                  <th className="px-4 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.products.map((p) => (
                  <tr key={p.id} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-2">{p.title}</td>
                    <td className="px-4 py-2">{p.category}</td>
                    <td className="px-4 py-2">{p.origin_country}</td>
                    <td className="px-4 py-2 text-right">
                      £{p.price_per_kg.toFixed(2)}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <Link href={`/products/edit/${p.id}`} prefetch={false}>
                        <a className="text-blue-600 hover:underline">
                          Edit
                        </a>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Sell product CTA */}
        <div className="mt-6 text-right">
          <Link href="/products/new" prefetch={false}>
            <a className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition">
              + Sell Product
            </a>
          </Link>
        </div>
      </main>
    </div>
  )
}