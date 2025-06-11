// File: frontend/pages/supplier/inventory.tsx
"use client"

import { useEffect, useState } from 'react'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import ProductCard from '@/components/ProductCard'

const INVENTORY_TABS = [
  { key: 'create',     label: 'Create Product' },
  { key: 'edit',       label: 'Edit Product' },
  { key: 'active',     label: 'Active Products' },
  { key: 'compliance', label: 'Compliance' },
]

interface Product {
  id: number
  title: string
  description?: string
  price_per_kg: number
  origin_country?: string
  category?: string
  image_url?: string
}

export default function SupplierInventory() {
  useAuthRedirect('supplier')

  // Dashboard data
  const [data,    setData]    = useState<{ products: Product[] } | null>(null)
  const [loading,setLoading] = useState(true)
  const [error,  setError]   = useState<string | null>(null)

  // Tabs
  const [activeTab,   setActiveTab]   = useState<'create'|'edit'|'active'|'compliance'>('create')
  const [refreshFlag, setRefreshFlag] = useState(0)
  const refreshDashboard = () => setRefreshFlag(f => f + 1)

  // Create form state
  const [title, setTitle]           = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice]           = useState('')
  const [origin, setOrigin]         = useState('')
  const [category, setCategory]     = useState('')
  const [imageFile, setImageFile]   = useState<File | null>(null)
  const [formError, setFormError]   = useState<string | null>(null)

  // Edit state
  const [editId, setEditId]                   = useState<number | ''>('')
  const [editTitle, setEditTitle]             = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [editPrice, setEditPrice]             = useState('')
  const [editOrigin, setEditOrigin]           = useState('')
  const [editCategory, setEditCategory]       = useState('')
  const [editError, setEditError]             = useState<string | null>(null)

  // Load dashboard data
  useEffect(() => {
    let m = true
    setLoading(true)
    api.get('/supplier/dashboard')
      .then(res => { if (m) setData(res.data) })
      .catch(err => { if (m) setError(err.message) })
      .finally(() => { if (m) setLoading(false) })
    return () => { m = false }
  }, [refreshFlag])

  if (loading) {
    return <p className="p-8 text-center">Loading inventory…</p>
  }
  if (error || !data) {
    return <p className="p-8 text-center text-red-600">{error || 'Error loading inventory'}</p>
  }

  // Pre-fill edit form when selection changes
  useEffect(() => {
    if (editId !== '' && data) {
      const prod = data.products.find(p => p.id === editId)
      if (prod) {
        setEditTitle(prod.title)
        setEditDescription(prod.description || '')
        setEditPrice(String(prod.price_per_kg))
        setEditOrigin(prod.origin_country || '')
        setEditCategory(prod.category || '')
      }
    }
  }, [editId, data])

  // Create handler
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
      await api.post('products', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      setTitle(''); setDescription(''); setPrice(''); setOrigin(''); setCategory(''); setImageFile(null)
      refreshDashboard()
      setActiveTab('active')
    } catch (err: any) {
      const detail = err.response?.data?.detail
      setFormError(typeof detail === 'string' ? detail : JSON.stringify(err.response?.data))
    }
  }

  // Edit handler
  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (editId === '') return
    setEditError(null)
    try {
      await api.put(`products/${editId}`, {
        title: editTitle,
        description: editDescription,
        price_per_kg: Number(editPrice),
        origin_country: editOrigin,
        category: editCategory,
      })
      setEditId('')
      refreshDashboard()
      setActiveTab('active')
    } catch (err: any) {
      const detail = err.response?.data?.detail
      setEditError(typeof detail === 'string' ? detail : 'Failed to update')
    }
  }

  return (
    <div className="bg-bg-page min-h-screen">
      <div className="h-16" />
      <main className="max-w-7xl mx-auto px-4 pt-5 space-y-8">
        <div className="bg-white dark:bg-gray-800 border rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b">
            <h2 className="text-2xl font-semibold">Manage Inventory</h2>
          </div>

          {/* Tabs */}
          <div className="px-4 pt-2">
            <nav className="flex space-x-4 overflow-x-auto">
              {INVENTORY_TABS.map(tab => (
                <button
                  key={tab.key}
                  onClick={() => { setActiveTab(tab.key as any); setEditId('') }}
                  className={`py-2 px-4 text-sm font-medium ${
                    activeTab === tab.key
                      ? 'border-b-2 border-black'
                      : 'text-gray-500'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          <div className="p-4 space-y-8">
            {/* CREATE */}
            {activeTab === 'create' && (
              <form onSubmit={handleCreateSubmit} className="space-y-4">
                {formError && <p className="text-red-600">{formError}</p>}
                <input
                  type="text"
                  placeholder="Title"
                  value={title}
                  onChange={e => setTitle(e.currentTarget.value)}
                  required
                  className="w-full p-2 border rounded"
                />
                <input
                  type="number"
                  placeholder="Price per kg"
                  value={price}
                  onChange={e => setPrice(e.currentTarget.value)}
                  required
                  className="w-full p-2 border rounded"
                />
                <input
                  type="text"
                  placeholder="Origin country"
                  value={origin}
                  onChange={e => setOrigin(e.currentTarget.value)}
                  className="w-full p-2 border rounded"
                />
                <input
                  type="text"
                  placeholder="Category"
                  value={category}
                  onChange={e => setCategory(e.currentTarget.value)}
                  className="w-full p-2 border rounded"
                />
                <textarea
                  placeholder="Description"
                  value={description}
                  onChange={e => setDescription(e.currentTarget.value)}
                  className="w-full p-2 border rounded"
                />
                <input
                  type="file"
                  accept="image/*"
                  onChange={e => setImageFile(e.target.files?.[0] ?? null)}
                  required
                  className="w-full"
                />
                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded">
                  Create Product
                </button>
              </form>
            )}

            {/* EDIT */}
            {activeTab === 'edit' && (
              <div className="space-y-6">
                <label className="block">
                  <span className="font-semibold">Select product to edit:</span>
                  <select
                    value={editId}
                    onChange={e => setEditId(Number(e.target.value))}
                    className="mt-2 p-2 border rounded w-full"
                  >
                    <option value="" disabled>-- pick one --</option>
                    {data.products.map(p => (
                      <option key={p.id} value={p.id}>
                        {p.title} (ID: {p.id})
                      </option>
                    ))}
                  </select>
                </label>

                {editId !== '' && (
                  <form onSubmit={handleEditSubmit} className="space-y-4">
                    {editError && <p className="text-red-600">{editError}</p>}
                    <input
                      name="title"
                      value={editTitle}
                      onChange={e => setEditTitle(e.currentTarget.value)}
                      placeholder="Title"
                      required
                      className="w-full p-2 border rounded"
                    />
                    <input
                      name="price_per_kg"
                      type="number"
                      placeholder="Price per kg"
                      value={editPrice}
                      onChange={e => setEditPrice(e.currentTarget.value)}
                      required
                      className="w-full p-2 border rounded"
                    />
                    <input
                      name="origin_country"
                      placeholder="Origin country"
                      value={editOrigin}
                      onChange={e => setEditOrigin(e.currentTarget.value)}
                      className="w-full p-2 border rounded"
                    />
                    <input
                      name="category"
                      placeholder="Category"
                      value={editCategory}
                      onChange={e => setEditCategory(e.currentTarget.value)}
                      className="w-full p-2 border rounded"
                    />
                    <textarea
                      name="description"
                      placeholder="Description"
                      value={editDescription}
                      onChange={e => setEditDescription(e.currentTarget.value)}
                      className="w-full p-2 border rounded"
                    />
                    <button
                      type="submit"
                      className="px-4 py-2 bg-green-600 text-white rounded"
                    >
                      Save Changes
                    </button>
                  </form>
                )}
              </div>
            )}

            {/* ACTIVE */}
            {activeTab === 'active' && (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {data.products.map(prod => (
                  <ProductCard key={prod.id} product={prod} />
                ))}
              </div>
            )}

            {/* COMPLIANCE */}
            {activeTab === 'compliance' && (
              <p className="text-gray-500 italic">Compliance coming soon.</p>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}