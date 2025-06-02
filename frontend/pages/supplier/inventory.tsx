import { useState } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import useSupplierDashboard from '@/hooks/useSupplierDashboard'
import CreateProductForm from '@/components/CreateProductForm'

// ----------------------------------------------------------------
// Only the four tabs we want to expose on the standalone Inventory page
// ----------------------------------------------------------------
const INVENTORY_TABS = [
  { key: 'create', label: 'Create Product' },
  { key: 'edit',   label: 'Edit Product' },
  { key: 'active', label: 'Active Products' },
  { key: 'compliance', label: 'Compliance' },
]

export default function SupplierInventory() {
  // 1) Enforce that only “supplier” can view this page
  useAuthRedirect('supplier')

  // 2) Fetch supplier-specific data (we’ll reuse it for “Edit” / “Active” tabs if needed)
  const { data, loading, error } = useSupplierDashboard()

  // 3) Track which inventory tab is active
  const [activeTab, setActiveTab] = useState<string>('create')

  // 4) Flag to trigger a refresh (after Create → re-fetch dashboard data)
  const [refreshFlag, setRefreshFlag] = useState<number>(0)
  const refreshDashboard = () => setRefreshFlag((f) => f + 1)

  // Show spinner if loading
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-page">
        <p className="text-text-secondary">Loading inventory…</p>
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

  return (
    <div className="bg-bg-page min-h-screen">
      {/* Spacer to account for sticky navbar height */}
      <div className="h-16" />

      <main className="max-w-7xl mx-auto px-4 pt-5 space-y-8">
        {/* ────────────────────────────────────────────────────────────────── */}
        {/* Manage Inventory Card (Standalone Page) */}
        {/* ────────────────────────────────────────────────────────────────── */}
        <div className="bg-white dark:bg-gray-800 border border-border-light dark:border-gray-700 rounded-lg">
          {/* Header */}
          <div className="px-4 py-3 border-b border-border-light dark:border-gray-700">
            <h2 className="text-2xl font-semibold text-text dark:text-text-secondary">
              Manage Inventory
            </h2>
          </div>

          {/* Tabs */}
          <div className="px-4 pt-2">
            <nav className="flex space-x-4 overflow-x-auto">
              {INVENTORY_TABS.map((tab) => {
                // Build the appropriate class string without backticks
                const isActive = activeTab === tab.key
                const baseClasses = 'py-2 px-4 text-sm font-medium whitespace-nowrap focus:outline-none'
                const activeClasses = 'border-b-2 border-black dark:border-white text-black dark:text-white'
                const inactiveClasses = 'text-text-secondary dark:text-text-secondary'
                const finalClassName = baseClasses + ' ' + (isActive ? activeClasses : inactiveClasses)

                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={finalClassName}
                  >
                    {tab.label}
                  </button>
                )
              })}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-4">
            {/* — Create Product Tab — */}
            {activeTab === 'create' && (
              <CreateProductForm onSuccess={refreshDashboard} />
            )}

            {/* — Edit Product Tab — */}
            {activeTab === 'edit' && (
              <div>
                <p className="text-text-secondary italic mb-4">
                  “Edit Product” form goes here.
                </p>
                {/*
                   TODO: Replace the paragraph above with a proper <EditProductForm />
                   when you build it. You can loop through data.products for the supplier’s products.
                */}
              </div>
            )}

            {/* — Active Products Tab — */}
            {activeTab === 'active' && (
              <div>
                <p className="text-text-secondary italic mb-4">
                  “Active Products” listing goes here.
                </p>
                {/*
                   TODO: Replace the paragraph above with a ProductTable or ProductCard list
                   that renders data.products so suppliers can manage their active listings.
                */}
              </div>
            )}

            {/* — Compliance Tab — */}
            {activeTab === 'compliance' && (
              <div>
                <p className="text-text-secondary italic">
                  “Compliance” section goes here.
                </p>
                {/*
                   TODO: Insert your compliance UI (KYC status, document uploads, etc.).
                */}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}