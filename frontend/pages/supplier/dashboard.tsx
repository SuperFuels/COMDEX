// frontend/pages/supplier/dashboard.tsx

import { useEffect, useState } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import useSupplierDashboard from '@/hooks/useSupplierDashboard'
import Chart, { ChartPoint } from '@/components/Chart'

// ----------------------------------------------------------------
// Metrics used at the top (we'll print all of them instead of choosing one)
// ----------------------------------------------------------------
const METRICS = [
  { key: 'totalSalesToday', label: 'Sales Today' },
  { key: 'activeListings',   label: 'Active Listings' },
  { key: 'openOrders',       label: 'Open Orders' },
  { key: 'proceeds30d',      label: '30d Proceeds' },
  { key: 'feedbackRating',   label: 'Feedback' },
]

// ----------------------------------------------------------------
// Inventory tabs—including "Create Product" and "Shipments"
// ----------------------------------------------------------------
const INVENTORY_TABS = [
  { key: 'create',     label: 'Create Product' },
  { key: 'edit',       label: 'Edit Product' },
  { key: 'active',     label: 'Active Products' },
  { key: 'messages',   label: 'Messages' },
  { key: 'compliance', label: 'Compliance' },
  { key: 'reports',    label: 'Reports' },
  { key: 'shipments',  label: 'Shipments' },
]

// ----------------------------------------------------------------
// Inline "Create Product" form (exactly as before)
// ----------------------------------------------------------------
function CreateProductForm({ onSuccess }: { onSuccess: () => void }) {
  const [formData, setFormData] = useState({
    title: '',
    origin_country: '',
    category: '',
    description: '',
    price_per_kg: '',
    image: null as File | null,
  })
  const [error, setError] = useState('')

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, files } = e.target as any
    if (name === 'image' && files && files.length > 0) {
      setFormData(f => ({ ...f, image: files[0] }))
    } else {
      setFormData(f => ({ ...f, [name]: value }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    const data = new FormData()
    data.append('title', formData.title)
    data.append('origin_country', formData.origin_country)
    data.append('category', formData.category)
    data.append('description', formData.description)
    data.append('price_per_kg', formData.price_per_kg)
    if (formData.image) {
      data.append('image', formData.image)
    }

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/products`, {
        method: 'POST',
        headers: {
          // When using multipart/form-data, do NOT set Content-Type manually.
          Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: data,
      })
      if (!res.ok) {
        const json = await res.json()
        throw new Error(json.detail || 'Upload failed.')
      }
      // Clear form fields and notify parent to refresh dashboard data
      setFormData({
        title: '',
        origin_country: '',
        category: '',
        description: '',
        price_per_kg: '',
        image: null,
      })
      onSuccess()
    } catch (err: any) {
      setError(err.message || 'Upload failed.')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <p className="text-red-600">{error}</p>}

      <div className="space-y-1">
        <label htmlFor="title" className="block text-sm font-medium text-gray-700">
          Title
        </label>
        <input
          id="title"
          name="title"
          value={formData.title}
          onChange={handleChange}
          placeholder="e.g. Organic Whey Protein"
          className="
            block w-full
            px-4 py-2
            bg-white
            border border-gray-300
            rounded-md
            text-gray-800 text-sm
            placeholder-gray-400
            focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent
          "
          required
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="origin_country" className="block text-sm font-medium text-gray-700">
          Country of Origin
        </label>
        <input
          id="origin_country"
          name="origin_country"
          value={formData.origin_country}
          onChange={handleChange}
          placeholder="e.g. USA"
          className="
            block w-full
            px-4 py-2
            bg-white
            border border-gray-300
            rounded-md
            text-gray-800 text-sm
            placeholder-gray-400
            focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent
          "
          required
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="category" className="block text-sm font-medium text-gray-700">
          Category (e.g. Whey)
        </label>
        <input
          id="category"
          name="category"
          value={formData.category}
          onChange={handleChange}
          placeholder="e.g. Whey Protein"
          className="
            block w-full
            px-4 py-2
            bg-white
            border border-gray-300
            rounded-md
            text-gray-800 text-sm
            placeholder-gray-400
            focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent
          "
          required
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="description" className="block text-sm font-medium text-gray-700">
          Description
        </label>
        <textarea
          id="description"
          name="description"
          value={formData.description}
          onChange={handleChange}
          rows={3}
          placeholder="Short description of your product"
          className="
            block w-full
            px-4 py-2
            bg-white
            border border-gray-300
            rounded-md
            text-gray-800 text-sm
            placeholder-gray-400
            focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent
          "
          required
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="price_per_kg" className="block text-sm font-medium text-gray-700">
          Price per KG (£)
        </label>
        <input
          id="price_per_kg"
          name="price_per_kg"
          type="number"
          step="0.01"
          value={formData.price_per_kg}
          onChange={handleChange}
          placeholder="e.g. 12.50"
          className="
            block w-full
            px-4 py-2
            bg-white
            border border-gray-300
            rounded-md
            text-gray-800 text-sm
            placeholder-gray-400
            focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent
          "
          required
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="image" className="block text-sm font-medium text-gray-700">
          Product Image
        </label>
        <input
          id="image"
          name="image"
          type="file"
          accept="image/*"
          onChange={handleChange}
          className="block w-full text-gray-700 text-sm"
          required
        />
      </div>

      <div>
        <button
          type="submit"
          className="
            inline-flex justify-center items-center
            px-6 py-2
            bg-blue-600 text-white
            font-medium text-sm
            rounded-md
            hover:bg-blue-700
            focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2
            transition
          "
        >
          Upload
        </button>
      </div>
    </form>
  )
}

// ----------------------------------------------------------------
// Main SupplierDashboard component
// ----------------------------------------------------------------
export default function SupplierDashboard() {
  // 1) If user is not a supplier, they will be redirected
  useAuthRedirect('supplier')

  // 2) Fetch supplier‐specific data (e.g. sales, listings, etc.)
  const { data, loading, error } = useSupplierDashboard()

  // 3) Track which inventory tab is active
  const [activeTab, setActiveTab] = useState<string>('create')

  // 4) For reloading the dashboard after creating a product
  const [refreshFlag, setRefreshFlag] = useState<number>(0)
  const refreshDashboard = () => setRefreshFlag((f) => f + 1)

  // Show spinner if loading
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-page">
        <p className="text-text-secondary">Loading dashboard…</p>
      </div>
    )
  }

  // Show error if any
  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-page">
        <p className="text-red-600">{error || 'Unknown error'}</p>
      </div>
    )
  }

  // Extract all metric values
  const metricsOutput = METRICS.map((m) => {
    const rawValue = (data as any)[m.key]
    // Format proceeds30d with “£”
    if (m.key === 'proceeds30d') {
      return { label: m.label, value: `£${rawValue}`, color: 'text-blue-600' }
    }
    // Color‐code “Feedback” as purple, “Sales Today” as blue, “Active Listings” & “Open Orders” as green
    if (m.key === 'feedbackRating') {
      return { label: m.label, value: rawValue, color: 'text-purple-600' }
    }
    if (m.key === 'totalSalesToday') {
      return { label: m.label, value: rawValue, color: 'text-blue-600' }
    }
    // activeListings and openOrders are green
    return { label: m.label, value: rawValue, color: 'text-green-600' }
  })

  // Build a dummy 24‐point time series to feed into <Chart>
  const sampleChartData: ChartPoint[] = Array.from({ length: 24 }, (_, i) => ({
    time: Math.floor(Date.now() / 1000) - (23 - i) * 3600,
    value:
      (data.products.length > 0 ? data.products[0].price_per_kg : 1) * 1000 +
      (Math.random() - 0.5) * 500,
  }))

  return (
    <div className="bg-bg-page min-h-screen">
      {/* ─── (NO EXTRA SPACER) ──────────────────────────────────── */}
      {/* _app.tsx already has pt-16 for the sticky navbar, so we do NOT need a div.h-16 here */}

      <main className="max-w-7xl mx-auto px-4 pt-5 space-y-8">
        {/* ── Global Snapshot + AI “Central Command” ─────────────────────────────────── */}
        <div className="bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg">
          {/* Card Header */}
          <div className="p-4">
            <h2 className="text-lg font-semibold text-text dark:text-text-secondary">
              Global Snapshot
            </h2>
          </div>

          {/* All Metrics (monospace, color‐coded) */}
          <div className="border-t border-border-light dark:border-gray-700 px-4 pt-4 font-mono bg-white dark:bg-gray-800 text-text dark:text-text-secondary text-sm space-y-1">
            {metricsOutput.map((m) => (
              <p key={m.label}>
                <span>{`“${m.label}”: `}</span>
                <span className={`${m.color}`}>{m.value}</span>
              </p>
            ))}
          </div>

          {/* Divider */}
          <hr className="border-border-light dark:border-gray-700" />

          {/* Left/Right Split: Buttons (left) + AI Terminal (right) */}
          <div className="flex h-48 overflow-hidden">
            {/* ——— Left Column: Vertical Buttons ——— */}
            <div className="w-1/4 border-r border-border-light dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-2 space-y-2 overflow-y-auto">
              {['Sales', 'Marketing', 'Operations', 'Shipments', 'Financials', 'Clients'].map((btn) => (
                <button
                  key={btn}
                  onClick={() => {
                    /* TODO: hook into AI to fetch “${btn}” report */
                  }}
                  className="
                    w-full text-left
                    px-3 py-2
                    bg-white dark:bg-gray-800
                    border border-gray-300 dark:border-gray-700
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

            {/* ——— Right Column: AI “Terminal” ——— */}
            <div className="flex-1 p-4 bg-white dark:bg-gray-800 overflow-auto font-mono text-text dark:text-text-secondary text-sm space-y-2">
              <p>→ Welcome to Central Command</p>
              <p>→ Type a question or click one of the buttons on the left</p>
              <p>[…AI will respond here…]</p>
            </div>
          </div>
        </div>

        {/* ── “Manage Inventory” Tabbed Container ────────────────────────────── */}
        <div className="bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg">
          {/* Header */}
          <div className="px-4 py-3 border-b border-border-light dark:border-gray-700">
            <h2 className="text-xl font-semibold text-text dark:text-text-secondary">
              Manage Inventory
            </h2>
          </div>

          {/* Tabs */}
          <div className="px-4 pt-2">
            <nav className="flex space-x-4 overflow-x-auto">
              {INVENTORY_TABS.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`
                    py-2 px-4 text-sm font-medium whitespace-nowrap
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

          {/* Tab Content */}
          <div className="p-4">
            {/* ── Create Product Tab ──────────────────────────────────────────── */}
            {activeTab === 'create' && (
              <CreateProductForm onSuccess={refreshDashboard} />
            )}

            {/* ── Edit Product Tab ───────────────────────────────────────────── */}
            {activeTab === 'edit' && (
              <p className="text-text-secondary italic">
                “Edit Product” form goes here.
              </p>
            )}

            {/* ── Active Products Tab ───────────────────────────────────────── */}
            {activeTab === 'active' && (
              <p className="text-text-secondary italic">
                “Active Products” listing goes here.
              </p>
            )}

            {/* ── Messages Tab ───────────────────────────────────────────────── */}
            {activeTab === 'messages' && (
              <p className="text-text-secondary italic">
                “Messages” inbox/chat goes here.
              </p>
            )}

            {/* ── Compliance Tab ─────────────────────────────────────────────── */}
            {activeTab === 'compliance' && (
              <p className="text-text-secondary italic">
                “Compliance” section goes here.
              </p>
            )}

            {/* ── Reports Tab: now shows the <Chart> ────────────────────────── */}
            {activeTab === 'reports' && (
              <div className="h-64 overflow-hidden">
                <Chart data={sampleChartData} height={256} />
              </div>
            )}

            {/* ── Shipments Tab ──────────────────────────────────────────────── */}
            {activeTab === 'shipments' && (
              <p className="text-text-secondary italic">
                “Shipments” tracking goes here.
              </p>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}