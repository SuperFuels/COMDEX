// File: frontend/pages/supplier/inventory.tsx
"use client"

import { useEffect, useState } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import InventoryCreate from '@/components/InventoryCreate'
import InventoryEdit   from '@/components/InventoryEdit'
import InventoryActive from '@/components/InventoryActive'

const TABS = ['create','edit','active','compliance'] as const

export default function SupplierInventory() {
  // Only suppliers may view this page
  useAuthRedirect('supplier')

  // State for the list of products
  const [products, setProducts] = useState<any[]>([])
  const [loading, setLoading]   = useState(true)
  // Which tab is active
  const [tab, setTab]           = useState<typeof TABS[number]>('create')

  // Fetch products from dashboard endpoint
  const reload = () => {
    setLoading(true)
    api.get('/supplier/dashboard')
      .then(res => setProducts(res.data.products))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(reload, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-page">
        <p className="text-text-secondary">Loading inventory…</p>
      </div>
    )
  }

  return (
    <div className="bg-bg-page min-h-screen p-4">
      <h2 className="text-2xl font-semibold mb-4">Manage Inventory</h2>

      {/* Tab Navigation */}
      <nav className="flex space-x-2 mb-6">
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={
              `px-4 py-2 rounded ${
                tab === t ? 'bg-gray-200' : 'bg-white'
              }`
            }
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </nav>

      {/* Active Tab Panel */}
      <div className="bg-white rounded-lg p-6 shadow">
        {tab === 'create' && <InventoryCreate onCreated={reload} />}

        {tab === 'edit' && (
          <InventoryEdit products={products} onEdited={reload} />
        )}

        {tab === 'active' && (
          <InventoryActive products={products} />
        )}

        {tab === 'compliance' && (
          <p className="text-gray-500 italic">Compliance coming soon.</p>
        )}
      </div>
    </div>
  )
}