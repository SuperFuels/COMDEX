// File: frontend/pages/supplier/inventory.tsx
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
  // 1) Enforce that only suppliers can view
  useAuthRedirect('supplier')

  // 2) Dashboard data
  const [data,    setData]    = useState<any>(null)
  const [loading,setLoading] = useState(true)
  const [error,  setError]   = useState<string | null>(null)

  // 3) Tab state & refresh
  const [activeTab,   setActiveTab]   = useState<string>('create')
  const [refreshFlag, setRefreshFlag] = useState(0)
  const refreshDashboard = () => setRefreshFlag(f => f + 1)

  // 4) Create form state
  const [title, setTitle]           = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice]           = useState('')
  const [origin, setOrigin]         = useState('')
  const [category, setCategory]     = useState('')
  const [imageFile, setImageFile]   = useState<File | null>(null)
  const [formError, setFormError]   = useState<string | null>(null)

  // 5) Edit form state
  const [editId, setEditId]                   = useState<number | null>(null)
  const [editTitle, setEditTitle]             = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [editPrice, setEditPrice]             = useState('')
  const [editOrigin, setEditOrigin]           = useState('')
  const [editCategory, setEditCategory]       = useState('')
  const [editError, setEditError]             = useState<string | null>(null)

  // 6) Fetch dashboard data on mount & when refreshFlag changes
  useEffect(() => {
    let mounted = true
    setLoading(true)
    api.get('/supplier/dashboard')
      .then(res => { if (mounted) setData(res.data) })
      .catch(err => { if (mounted) setError(err.message) })
      .finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [refreshFlag])

  if (loading) {
    return <p className="p-8 text-center">Loading inventory…</p>
  }
  if (error || !data) {
    return <p className="p-8 text-center text-red-600">{error || 'Error loading inventory'}</p>
  }

  // 7) Prefill edit form when editId changes
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

  // 8) Create handler
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    if (!imageFile) {
      setFormError('Please select an image.')
      return
    }
    const fd = new FormData()
    fd.append('title', title)
    fd.append('description', description)
    fd.append('price_per_kg', price)
    fd.append('origin_country', origin)
    fd.append('category', category)
    fd.append('image', imageFile)
    try {
      await api.post('products', fd, { headers: { 'Content-Type': 'multipart/form-data' }})
      // reset form
      setTitle(''); setDescription(''); setPrice(''); setOrigin(''); setCategory(''); setImageFile(null)
      refreshDashboard()
      setActiveTab('active')
    } catch (err: any) {
      setFormError(err.response?.data?.detail || 'Failed to create product.')
    }
  }

  // 9) Edit handler
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (editId == null) return
    setEditError(null)
    try {
      await api.put(`products/${editId}`, {
        title: editTitle,
        description: editDescription,
        price_per_kg: Number(editPrice),
        origin_country: editOrigin,
        category: editCategory,
      })
      // reset & refresh
      setEditId(null)
      refreshDashboard()
      setActiveTab('active')
    } catch (err: any) {
      setEditError(err.response?.data?.detail || 'Failed to update product.')
    }
  }

  // 10) Render
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
                    onClick={() => { setActiveTab(tab.key); setEditId(null) }}
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
          <div className="p-4 space-y-8">
            {/* CREATE */}
            {activeTab === 'create' && (
              <form onSubmit={handleCreateSubmit} className="space-y-4">
                {formError && <p className="text-red-600">{formError}</p>}
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
                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded">Create Product</button>
              </form>
            )}

            {/* EDIT */}
            {activeTab === 'edit' && (
              <div className="space-y-6">
                <label className="block">
                  <span className="font-semibold">Select a product to edit:</span>
                  <select
                    className="mt-1 p-2 border rounded w-full"
                    value={editId ?? ''}
                    onChange={e => setEditId(Number(e.target.value))}
                  >
                    <option value="" disabled>-- pick one --</option>
                    {data.products.map((p: any) => (
                      <option key={p.id} value={p.id}>
                        {p.title} (ID: {p.id})
                      </option>
                    ))}
                  </select>
                </label>

                {editId != null && (
                  <form onSubmit={handleEditSubmit} className="space-y-4">
                    {editError && <p className="text-red-600">{editError}</p>}
                    <input
                      type="text" placeholder="Title"
                      value={editTitle} onChange={e => setEditTitle(e.currentTarget.value)}
                      required className="w-full p-2 border rounded"
                    />
                    <input
                      type="number" placeholder="Price per kg"
                      value={editPrice} onChange={e => setEditPrice(e.currentTarget.value)}
                      required className="w-full p-2 border rounded"
                    />
                    <input
                      type="text" placeholder="Origin country"
                      value={editOrigin} onChange={e => setEditOrigin(e.currentTarget.value)}
                      className="w-full p-2 border rounded"
                    />
                    <input
                      type="text" placeholder="Category"
                      value={editCategory} onChange={e => setEditCategory(e.currentTarget.value)}
                      className="w-full p-2 border rounded"
                    />
                    <textarea
                      placeholder="Description"
                      value={editDescription} onChange={e => setEditDescription(e.currentTarget.value)}
                      className="w-full p-2 border rounded"
                    />
                    <button type="submit" className="px-4 py-2 bg-green-600 text-white rounded">
                      Save Changes
                    </button>
                  </form>
                )}
              </div>
            )}

            {/* ACTIVE */}
            {activeTab === 'active' && (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {data.products.map((prod: any) => (
                  <Link key={prod.id} href={`/products/${prod.id}`}>
                    <a><ProductCard product={prod} /></a>
                  </Link>
                ))}
              </div>
            )}

            {/* COMPLIANCE */}
            {activeTab === 'compliance' && (
              <p className="text-text-secondary italic">Compliance coming soon.</p>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}