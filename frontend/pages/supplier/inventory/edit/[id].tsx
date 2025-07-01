// File: frontend/pages/supplier/inventory/edit/[id].tsx
"use client"

import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import api from '@/lib/api'

interface Product {
  id: number
  title: string
  description?: string
  price_per_kg: number
  origin_country?: string
  category?: string
}

export default function EditInventoryItem() {
  const router = useRouter()
  const { id } = router.query as { id?: string }

  const [product, setProduct] = useState<Product | null>(null)
  const [form, setForm] = useState({
    title: '',
    description: '',
    price_per_kg: '',
    origin_country: '',
    category: '',
  })
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    api.get<Product>(`/products/${id}`)
      .then(({ data }) => {
        setProduct(data)
        setForm({
          title: data.title,
          description: data.description || '',
          price_per_kg: String(data.price_per_kg),
          origin_country: data.origin_country || '',
          category: data.category || '',
        })
      })
      .catch(() => setError('Failed to load product'))
      .finally(() => setLoading(false))
  }, [id])

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!id) return
    setError(null)
    try {
      await api.put(`/products/${id}`, {
        title: form.title,
        description: form.description,
        price_per_kg: parseFloat(form.price_per_kg),
        origin_country: form.origin_country,
        category: form.category,
      })
      router.push('/supplier/inventory')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update product')
    }
  }

  if (loading) {
    return <p className="p-8 text-center">Loading…</p>
  }
  if (error) {
    return <p className="p-8 text-center text-red-600">{error}</p>
  }
  if (!product) {
    return <p className="p-8 text-center">Product not found</p>
  }

  return (
    <main className="flex-1 bg-bg-page px-4 pt-0">
      <div className="max-w-lg mx-auto py-6">
        <h1 className="text-2xl font-bold mb-4">Edit Product #{product.id}</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            name="title"
            value={form.title}
            onChange={handleChange}
            placeholder="Title"
            required
            className="w-full p-2 border rounded"
          />
          <textarea
            name="description"
            value={form.description}
            onChange={handleChange}
            placeholder="Description"
            className="w-full p-2 border rounded"
          />
          <input
            name="price_per_kg"
            type="number"
            step="0.01"
            value={form.price_per_kg}
            onChange={handleChange}
            placeholder="Price per kg"
            required
            className="w-full p-2 border rounded"
          />
          <input
            name="origin_country"
            value={form.origin_country}
            onChange={handleChange}
            placeholder="Origin country"
            className="w-full p-2 border rounded"
          />
          <input
            name="category"
            value={form.category}
            onChange={handleChange}
            placeholder="Category"
            className="w-full p-2 border rounded"
          />
          <button
            type="submit"
            className="w-full py-2 bg-green-600 text-white rounded hover:bg-green-700"
          >
            Save Changes
          </button>
        </form>
      </div>
    </main>
  )
}