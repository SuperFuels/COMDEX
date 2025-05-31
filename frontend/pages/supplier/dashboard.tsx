// frontend/pages/supplier/dashboard.tsx
import { useEffect, useState } from 'react'
import Link from 'next/link'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import useSupplierDashboard from '@/hooks/useSupplierDashboard'
import Image from 'next/image'

export default function SupplierDashboard() {
  // Only suppliers may see this page:
  useAuthRedirect('supplier')

  const { data, loading, error } = useSupplierDashboard()

  // Local state: which metric is selected
  type MetricKey = 'Sales Today' | 'Active Listings' | 'Open Orders' | '30d Proceeds' | 'Feedback'
  const metricOptions: MetricKey[] = [
    'Sales Today',
    'Active Listings',
    'Open Orders',
    '30d Proceeds',
    'Feedback'
  ]
  const [selectedMetric, setSelectedMetric] = useState<MetricKey>('Sales Today')

  // Helper: get the numeric value as a string for each metric
  const getMetricValue = () => {
    if (!data) return '0'
    switch (selectedMetric) {
      case 'Sales Today':
        return String(data.totalSalesToday)
      case 'Active Listings':
        return String(data.activeListings)
      case 'Open Orders':
        return String(data.openOrders)
      case '30d Proceeds':
        return `£${data.proceeds30d}`
      case 'Feedback':
        return String(data.feedbackRating)
      default:
        return '0'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background-page dark:bg-background-dark">
        <p className="text-text-light">Loading dashboard…</p>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background-page dark:bg-background-dark">
        <p className="text-red-600">{error || 'Unknown error'}</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background-page dark:bg-background-dark pb-8">
      {/* ===== Sticky SwapBar + Navbar are rendered in _app.tsx ===== */}

      {/* ===== “Terminal‐style” metric container ===== */}
      <div className="max-w-7xl mx-auto px-4 pt-6">
        <div className="bg-white dark:bg-background-dark border border-border-light dark:border-border-light-dark rounded-lg shadow p-4">
          <div className="flex items-center mb-2">
            {/* Dropdown icon on the left using g.svg */}
            <Image
              src="/g.svg"
              alt="Toggle"
              width={20}
              height={20}
              className="mr-2"
            />

            {/* “Metric:” label */}
            <label htmlFor="metric-select" className="text-text dark:text-text-light font-medium">
              Metric:
            </label>

            {/* Native <select> styled to match theme */}
            <select
              id="metric-select"
              value={selectedMetric}
              onChange={(e) => setSelectedMetric(e.target.value as MetricKey)}
              className="
                ml-2
                border border-gray-300 dark:border-border-light-dark
                bg-white dark:bg-background-dark
                text-text dark:text-text-light
                rounded px-2 py-1
                focus:outline-none focus:ring-2 focus:ring-primary
                transition
              "
            >
              {metricOptions.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          {/* “Terminal‐style” output: use <pre> with font-mono, light grey background */}
          <pre className="
            w-full
            font-mono text-text-dark dark:text-text-light
            bg-gray-50 dark:bg-gray-800
            border border-gray-200 dark:border-border-light-dark
            rounded
            p-4
            whitespace-pre-wrap
            text-sm
            overflow-x-auto
          ">
            {/* Show the text “Sales Today: 0” (or whatever metric) */}
            <span className="text-text dark:text-text-light">
              {selectedMetric}:
            </span>{' '}
            <span className="text-blue-600 font-normal">
              {getMetricValue()}
            </span>
          </pre>
        </div>
      </div>

      {/* ===== Dummy chart placeholders (2 side by side on large screens) ===== */}
      <div className="max-w-7xl mx-auto px-4 mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="
          bg-white dark:bg-background-dark
          border border-border-light dark:border-border-light-dark
          rounded-lg shadow
          h-64 flex items-center justify-center text-gray-400 dark:text-gray-500
        ">
          Chart placeholder
        </div>
        <div className="
          bg-white dark:bg-background-dark
          border border-border-light dark:border-border-light-dark
          rounded-lg shadow
          h-64 flex items-center justify-center text-gray-400 dark:text-gray-500
        ">
          Chart placeholder
        </div>
      </div>

      {/* ===== “My Listings” table + Sell Product button ===== */}
      <div className="max-w-7xl mx-auto px-4 mt-8">
        <div className="bg-white dark:bg-background-dark border border-border-light dark:border-border-light-dark rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold text-text dark:text-text-light mb-4">
            My Listings
          </h2>
          {data.products.length === 0 ? (
            <p className="text-text-light">You have no active listings yet.</p>
          ) : (
            <table className="min-w-full table-auto">
              <thead className="bg-gray-100 dark:bg-gray-700">
                <tr>
                  <th className="px-4 py-2 text-left text-text dark:text-text-light">Title</th>
                  <th className="px-4 py-2 text-left text-text dark:text-text-light">Category</th>
                  <th className="px-4 py-2 text-left text-text dark:text-text-light">Origin</th>
                  <th className="px-4 py-2 text-right text-text dark:text-text-light">Price / kg</th>
                  <th className="px-4 py-2 text-right text-text dark:text-text-light">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.products.map((p) => (
                  <tr key={p.id} className="border-t border-border-light dark:border-border-light-dark">
                    <td className="px-4 py-2 text-text dark:text-text-light">{p.title}</td>
                    <td className="px-4 py-2 text-text dark:text-text-light">{p.category}</td>
                    <td className="px-4 py-2 text-text dark:text-text-light">{p.origin_country}</td>
                    <td className="px-4 py-2 text-right text-text dark:text-text-light">
                      £{p.price_per_kg.toFixed(2)}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <Link href={`/products/edit/${p.id}`} prefetch={false}>
                        <a className="text-blue-600 hover:underline dark:text-blue-400">
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

        <div className="text-right mt-4">
          <Link href="/products/new" prefetch={false}>
            <a className="
              bg-blue-600 hover:bg-blue-700
              text-white
              px-4 py-2
              rounded
              focus:outline-none focus:ring-2 focus:ring-primary
              transition
            ">
              + Sell Product
            </a>
          </Link>
        </div>
      </div>
    </div>
  )
}