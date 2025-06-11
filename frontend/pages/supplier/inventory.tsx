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
    let m = true
    setLoading(true)
    api.get('/supplier/dashboard')
      .then(res => { if (m) setData(res.data) })
      .catch(err => { if (m) setError(err.message) })
      .finally(() => { if (m) setLoading(false) })
    return () => { m = false }
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

  // Pre-fill edit form
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

  // Handlers (reuse your existing logic)
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)
    if (!imageFile) return setFormError('Please select an image.')
    const fd = new FormData()
    fd.append('title', title)
    fd.append('description', description)
    fd.append('price_per_kg', price)
    fd.append('origin_country', origin)
    fd.append('category', category)
    fd.append('image', imageFile)
    try {
      await api.post('products', fd, { headers: { 'Content-Type': 'multipart/form-data' }})
      setTitle(''); setDescription(''); setPrice(''); setOrigin(''); setCategory(''); setImageFile(null)
      refreshDashboard()
      setActiveTab('active')
    } catch (err: any) {
      setFormError(err.response?.data?.detail || 'Error creating product.')
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
      setEditFormError(err.response?.data?.detail || 'Error updating product.')
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
          <div className="p-4">
            {/* CREATE */}
            {activeTab === 'create' && (
              <form onSubmit={handleCreateSubmit} className="space-y-4">
                {formError && <div className="text-red-600">{formError}</div>}
                {/* ... your create inputs ... */}
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
                        src={`${process.env.NEXT_PUBLIC_API_URL}${prod.image_url}`}
                        alt={prod.title}
                        className="h-32 w-full object-cover mb-2"
                      />
                      <h3 className="font-medium">{prod.title}</h3>
                      <p className="text-sm text-text-secondary">
                        £{prod.price_per_kg}/kg
                      </p>
                    </button>
                  ))}
                </div>
                {editId != null && (
                  <form onSubmit={handleEditSubmit} className="mt-6 space-y-3">
                    {editFormError && <p className="text-red-600">{editFormError}</p>}
                    {/* ... your edit inputs ... */}
                  </form>
                )}
              </div>
            )}

            {/* ACTIVE */}
            {activeTab === 'active' && (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {data.products.map((prod: any) => (
                  <Link key={prod.id} href={`/products/${prod.id}`}>
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
        </div>
      </main>
    </div>
  )
}