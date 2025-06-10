// File: frontend/pages/supplier/inventory.tsx
"use client"

import { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'
import ProductCard from '@/components/ProductCard'

const INVENTORY_TABS = [
  { key: 'create',     label: 'Create Product' },
  { key: 'edit',       label: 'Edit Product' },
  { key: 'active',     label: 'Active Products' },
  { key: 'compliance', label: 'Compliance' },
]

export default function SupplierInventory() {
  useAuthRedirect('supplier')
  const router = useRouter()

  const [data, setData]       = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  const [activeTab, setActiveTab]       = useState<string>('create')
  const [refreshFlag, setRefreshFlag]   = useState(0)
  const refreshDashboard = () => setRefreshFlag(f => f + 1)

  // Create form state
  const [title, setTitle]             = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice]             = useState('')
  const [origin, setOrigin]           = useState('')
  const [category, setCategory]       = useState('')
  const [imageFile, setImageFile]     = useState<File | null>(null)
  const [formError, setFormError]     = useState<string | null>(null)

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

  // Pre-fill edit form
  useEffect(() => {
    if (editId != null && data) {
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

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    if (!imageFile) return setFormError('Image required')

    const fd = new FormData()
    fd.append('title', title)
    fd.append('description', description)
    fd.append('price_per_kg', price)
    fd.append('origin_country', origin)
    fd.append('category', category)
    fd.append('image', imageFile)

    try {
      await api.post('products', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      // reset and refresh
      setTitle(''); setDescription(''); setPrice(''); setOrigin(''); setCategory(''); setImageFile(null)
      refreshDashboard()
      setActiveTab('active')
    } catch (err: any) {
      setFormError(err.response?.data?.detail || 'Error')
    }
  }

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (editId == null) return
    setEditFormError(null)
    try {
      await api.put(`products/${editId}`, {
        title: editTitle,
        description: editDescription,
        price_per_kg: Number(editPrice),
        origin_country: editOrigin,
        category: editCategory,
      })
      refreshDashboard()
      setEditId(null)
      setActiveTab('active')
    } catch (err: any) {
      setEditFormError(err.response?.data?.detail || 'Error')
    }
  }

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
          {/* CREATE */}
          {activeTab === 'create' && (
            <form onSubmit={handleCreateSubmit} className="space-y-3">
              {formError && <p className="text-red-600">{formError}</p>}
              <input value={title} onChange={e=>setTitle(e.currentTarget.value)}
                required placeholder="Title" className="w-full p-2 border rounded" />
              <input value={price} onChange={e=>setPrice(e.currentTarget.value)}
                required type="number" placeholder="Price per kg" className="w-full p-2 border rounded" />
              <input value={origin} onChange={e=>setOrigin(e.currentTarget.value)}
                placeholder="Origin country" className="w-full p-2 border rounded" />
              <input value={category} onChange={e=>setCategory(e.currentTarget.value)}
                placeholder="Category" className="w-full p-2 border rounded" />
              <textarea value={description} onChange={e=>setDescription(e.currentTarget.value)}
                placeholder="Description" className="w-full p-2 border rounded" />
              <input type="file" accept="image/*" onChange={e=>setImageFile(e.target.files?.[0]||null)} required />
              <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded">Create</button>
            </form>
          )}

          {/* EDIT */}
          {activeTab === 'edit' && (
            <div className="space-y-4">
              <p className="font-semibold">Select product to edit:</p>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {data.products.map((prod: any) => (
                  <button
                    key={prod.id}
                    onClick={() => setEditId(prod.id)}
                    className="border p-4 rounded hover:shadow cursor-pointer"
                  >
                    <img
                      src={`${process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '')}${prod.image_url}`}
                      alt={prod.title}
                      className="h-32 w-full object-cover mb-2"
                    />
                    <h3 className="font-medium">{prod.title}</h3>
                    <p className="text-sm text-text-secondary">£{prod.price_per_kg}/kg</p>
                  </button>
                ))}
              </div>
              {editId != null && (
                <form onSubmit={handleEditSubmit} className="mt-6 space-y-3">
                  {editFormError && <p className="text-red-600">{editFormError}</p>}
                  <input value={editTitle} onChange={e=>setEditTitle(e.currentTarget.value)}
                    required placeholder="Title" className="w-full p-2 border rounded" />
                  <input value={editPrice} onChange={e=>setEditPrice(e.currentTarget.value)}
                    required type="number" placeholder="Price per kg" className="w-full p-2 border rounded" />
                  <input value={editOrigin} onChange={e=>setEditOrigin(e.currentTarget.value)}
                    placeholder="Origin country" className="w-full p-2 border rounded" />
                  <input value={editCategory} onChange={e=>setEditCategory(e.currentTarget.value)}
                    placeholder="Category" className="w-full p-2 border rounded" />
                  <textarea value={editDescription} onChange={e=>setEditDescription(e.currentTarget.value)}
                    placeholder="Description" className="w-full p-2 border rounded" />
                  <button type="submit" className="px-4 py-2 bg-green-600 text-white rounded">Save Changes</button>
                </form>
              )}
            </div>
          )}

          {/* ACTIVE */}
          {activeTab === 'active' && (
            <div className="grid md:grid-cols-2 gap-4">
              {data.products.map((prod: any) => (
                <ProductCard key={prod.id} product={prod} onClick={() => router.push(`/products/${prod.id}`)} />
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