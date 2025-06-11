// File: frontend/pages/supplier/inventory.tsx
"use client"

import { useEffect, useState } from 'react'
import Link from 'next/link'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import ProductCard from '@/components/ProductCard'

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
  // Enforce supplier-only
  useAuthRedirect('supplier')

  // Dashboard data
  const [data,    setData]    = useState<any>(null)
  const [loading,setLoading] = useState(true)
  const [error,  setError]   = useState<string | null>(null)

  // Tab state
  const [activeTab,    setActiveTab]    = useState<string>('create')
  const [refreshFlag,  setRefreshFlag]  = useState(0)
  const refreshDashboard = () => setRefreshFlag(f => f + 1)

  // Create form state
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice] = useState('')
  const [origin, setOrigin] = useState('')
  const [category, setCategory] = useState('')
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  // Edit form state
  const [editId, setEditId]                   = useState<number | null>(null)
  const [editTitle, setEditTitle]             = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [editPrice, setEditPrice]             = useState('')
  const [editOrigin, setEditOrigin]           = useState('')
  const [editCategory, setEditCategory]       = useState('')
  const [editFormError, setEditFormError]     = useState<string | null>(null)

  // Fetch dashboard data
  useEffect(() => {
    let mounted = true
    setLoading(true)
    api.get('/supplier/dashboard')
      .then(res => { if (mounted) setData(res.data) })
      .catch(err => { if (mounted) setError(err.message) })
      .finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [refreshFlag])

  if (loading) return <p className="p-8 text-center">Loading…</p>
  if (error || !data) return <p className="p-8 text-center text-red-600">{error || 'Error'}</p>

  // Pre-fill edit form when a product is selected
  useEffect(() => {
    if (editId != null) {
      const prod = data.products.find((p: any) => p.id === editId)
      if (prod) {
        setEditTitle(prod.title)
        setEditDescription(prod.description || '')
        setEditPrice(String(prod.price_per_kg))
        setEditOrigin(prod.origin_country || '')
        setEditCategory(prod.category || '')
      }
    }
  }, [editId, data])

  // Handlers omitted for brevity—use your existing create/edit handlers

  return (
    <div className="bg-bg-page min-h-screen">
      <div className="h-16" />
      <main className="max-w-4xl mx-auto p-4 space-y-6 bg-white rounded-lg shadow">
        <h2 className="text-xl font-semibold">Manage Inventory</h2>

        {/* Tabs */}
        <nav className="flex space-x-2">
          {INVENTORY_TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => { setActiveTab(tab.key); setEditId(null) }}
              className={`px-3 py-1 border rounded ${
                activeTab === tab.key ? 'bg-gray-200' : 'bg-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Tab Panes */}
        <div>
          {/* CREATE & EDIT panes here… */}

          {/* ACTIVE */}
          {activeTab === 'active' && (
            <div className="grid md:grid-cols-2 gap-4">
              {data.products.map((prod: any) => (
                <Link
                  key={prod.id}
                  href={`/products/${prod.id}`}
                  passHref
                >
                  <a className="cursor-pointer">
                    <ProductCard product={prod} />
                  </a>
                </Link>
              ))}
            </div>
          )}

          {/* COMPLIANCE */}
          {activeTab === 'compliance' && (
            <p className="text-text-secondary italic">Compliance coming soon.</p>
          )}
        </div>
      </main>
    </div>
  )
}