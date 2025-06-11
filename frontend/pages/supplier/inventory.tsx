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
  useAuthRedirect('supplier')

  const [data,    setData]    = useState<any>(null)
  const [loading,setLoading] = useState(true)
  const [error,  setError]   = useState<string | null>(null)

  // Tab state
  const [activeTab,    setActiveTab]    = useState<string>('create')
  const [refreshFlag,  setRefreshFlag]  = useState(0)
  const refreshDashboard = () => setRefreshFlag(f => f + 1)

  // Form state for Create
  const [title, setTitle]             = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice]             = useState('')
  const [origin, setOrigin]           = useState('')
  const [category, setCategory]       = useState('')
  const [imageFile, setImageFile]     = useState<File | null>(null)
  const [formError, setFormError]     = useState<string | null>(null)

  // Fetch dashboard/inventory data
  useEffect(() => {
    let mounted = true
    setLoading(true)
    api.get('/supplier/dashboard')
      .then(res => { if (mounted) setData(res.data) })
      .catch(err => { if (mounted) setError(err.message || 'Error loading inventory') })
      .finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [refreshFlag])

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

  // Create handler
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    if (!imageFile) {
      setFormError('Please select an image.')
      return
    }
    const formData = new FormData()
    formData.append('title', title)
    formData.append('description', description)
    formData.append('price_per_kg', price)
    formData.append('origin_country', origin)
    formData.append('category', category)
    formData.append('image', imageFile)
    try {
      await api.post('products', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      setTitle(''); setDescription(''); setPrice(''); setOrigin(''); setCategory(''); setImageFile(null)
      refreshDashboard()
      setActiveTab('active')
    } catch (err: any) {
      const detail = err.response?.data?.detail
      setFormError(typeof detail === 'string' ? detail : JSON.stringify(err.response?.data))
    }
  }

  return (
    <div className="bg-bg-page min-h-screen">
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
              {INVENTORY_TABS.map(tab => {
                const isActive = activeTab === tab.key
                return (
                  <button
                    key={tab.key}
                    onClick={() => { setActiveTab(tab.key) }}
                    className={
                      `py-2 px-4 text-sm font-medium whitespace-nowrap focus:outline-none ` +
                      (isActive
                        ? 'border-b-2 border-black dark:border-white text-black dark:text-white'
                        : 'text-text-secondary dark:text-text-secondary')
                    }
                  >
                    {tab.label}
                  </button>
                )
              })}
            </nav>
          </div>

          {/* Content */}
          <div className="p-4">
            {/* CREATE */}
            {activeTab === 'create' && (
              <form onSubmit={handleCreateSubmit} className="space-y-4">
                {formError && <div className="text-red-600">{formError}</div>}
                <input
                  type="text" placeholder="Title"
                  value={title} onChange={e => setTitle(e.currentTarget.value)}
                  required className="w-full p-2 border rounded"
                />
                <input
                  type="number" placeholder="Price per kg"
                  value={price} onChange={e => setPrice(e.currentTarget.value)}
                  required className="w-full p-2 border rounded"
                />
                <input
                  type="text" placeholder="Origin country"
                  value={origin} onChange={e => setOrigin(e.currentTarget.value)}
                  className="w-full p-2 border rounded"
                />
                <input
                  type="text" placeholder="Category"
                  value={category} onChange={e => setCategory(e.currentTarget.value)}
                  className="w-full p-2 border rounded"
                />
                <textarea
                  placeholder="Description"
                  value={description} onChange={e => setDescription(e.currentTarget.value)}
                  className="w-full p-2 border rounded"
                />
                <input
                  type="file" accept="image/*"
                  onChange={e => setImageFile(e.target.files?.[0] ?? null)}
                  required className="w-full"
                />
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Create Product
                </button>
              </form>
            )}

            {/* EDIT */}
            {activeTab === 'edit' && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {data.products.map((prod: any) => (
                  <Link
                    key={prod.id}
                    href={`/supplier/inventory/edit/${prod.id}`}
                  >
                    <a className="border p-4 rounded hover:shadow">
                      <img
                        src={`${process.env.NEXT_PUBLIC_API_URL}${prod.image_url}`}
                        alt={prod.title}
                        className="h-32 w-full object-cover mb-2"
                      />
                      <h3 className="font-medium">{prod.title}</h3>
                      <p className="text-sm text-text-secondary">
                        £{prod.price_per_kg}/kg
                      </p>
                    </a>
                  </Link>
                ))}
              </div>
            )}

            {/* ACTIVE */}
            {activeTab === 'active' && (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {data.products.map((prod: any) => (
                  <ProductCard key={prod.id} product={prod} />
                ))}
              </div>
            )}

            {/* COMPLIANCE */}
            {activeTab === 'compliance' && (
              <p className="text-text-secondary italic">“Compliance” section coming soon.</p>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}