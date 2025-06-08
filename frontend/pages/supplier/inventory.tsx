// File: frontend/pages/supplier/inventory.tsx

import { useEffect, useState } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import CreateProductForm from '@/components/CreateProductForm'
import ProductCard from '@/components/ProductCard'    // <-- assume you have one

// ----------------------------------------------------------------
// Only the four tabs we want to expose on the standalone Inventory page
// ----------------------------------------------------------------
const INVENTORY_TABS = [
  { key: 'create',     label: 'Create Product' },
  { key: 'edit',       label: 'Edit Product' },
  { key: 'active',     label: 'Active Products' },
  { key: 'compliance', label: 'Compliance' },
]

export default function SupplierInventory() {
  // 1) Enforce that only “supplier” can view this page
  useAuthRedirect('supplier')

  // 2) Fetch supplier‐specific data
  const [data,    setData]    = useState<any>(null)
  const [loading,setLoading] = useState(true)
  const [error,  setError]   = useState<string | null>(null)

  // 3) Track which inventory tab is active
  const [activeTab,    setActiveTab]    = useState<string>('create')
  // 4) Flag to trigger a refresh (after Create → re‐fetch dashboard data)
  const [refreshFlag,  setRefreshFlag]  = useState(0)
  const refreshDashboard = () => setRefreshFlag((f) => f + 1)

  // Re-fetch any time `refreshFlag` changes
  useEffect(() => {
    let isMounted = true

    setLoading(true)
    api.get('/supplier/dashboard')
      .then((res) => {
        if (isMounted) {
          setData(res.data)
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Error loading inventory')
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [refreshFlag])

  // 5) Show loading / error states
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-page">
        <p className="text-text-secondary">Loading inventory…</p>
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

  return (
    <div className="bg-bg-page min-h-screen">
      {/* Spacer for sticky navbar */}
      <div className="h-16" />

      <main className="max-w-7xl mx-auto px-4 pt-5 space-y-8">
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
                const isActive = activeTab === tab.key
                const baseClasses = 'py-2 px-4 text-sm font-medium whitespace-nowrap focus:outline-none'
                const activeClasses   = 'border-b-2 border-black dark:border-white text-black dark:text-white'
                const inactiveClasses = 'text-text-secondary dark:text-text-secondary'
                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={`${baseClasses} ${isActive ? activeClasses : inactiveClasses}`}
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
              <p className="text-text-secondary italic">
                “Edit Product” form goes here. (Coming soon)
              </p>
            )}

            {/* — Active Products Tab — */}
            {activeTab === 'active' && (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {data.products.map((prod: any) => (
                  <ProductCard key={prod.id} product={prod} />
                ))}
              </div>
            )}

            {/* — Compliance Tab — */}
            {activeTab === 'compliance' && (
              <p className="text-text-secondary italic">
                “Compliance” section goes here. (Coming soon)
              </p>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}