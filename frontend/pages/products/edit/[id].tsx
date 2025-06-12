// File: frontend/pages/products/edit/[id].tsx
"use client"

import { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import api from '@/lib/api'

interface ProductForm {
  title: string
  description: string
  price_per_kg: string
  origin_country: string
  category: string
}

export default function EditProductPage() {
  const router = useRouter()
  const { id } = router.query

  const [form, setForm] = useState<ProductForm>({
    title: '',
    description: '',
    price_per_kg: '',
    origin_country: '',
    category: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return

    const fetchProduct = async () => {
      setLoading(true)
      try {
        const { data } = await api.get(`/products/${id}`)
        setForm({
          title: data.title,
          description: data.description,
          price_per_kg: String(data.price_per_kg),
          origin_country: data.origin_country,
          category: data.category,
        })
      } catch (err) {
        console.error(err)
        setError('❌ Failed to load product')
      } finally {
        setLoading(false)
      }
    }

    fetchProduct()
  }, [id])

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await api.put(`/products/${id}`, {
        title: form.title,
        description: form.description,
        price_per_kg: parseFloat(form.price_per_kg),
        origin_country: form.origin_country,
        category: form.category,
      })
      router.push('/dashboard')
    } catch (err) {
      console.error(err)
      setError('❌ Failed to update product')
    }
  }

  if (loading) return <p className="p-6 text-center">Loading product details…</p>

  return (
    <main className="min-h-screen bg-gray-100 pt-0">
      <div className="max-w-xl mx-auto mt-4 p-6 bg-white rounded shadow">
        <h1 className="text-2xl font-bold mb-4">✏️ Edit Product</h1>
        {error && <p className="text-red-500 mb-4">{error}</p>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            name="title"
            value={form.title}
            onChange={handleChange}
            placeholder="Title"
            required
            className="w-full border p-2 rounded"
          />

          <textarea
            name="description"
            value={form.description}
            onChange={handleChange}
            placeholder="Description"
            rows={4}
            required
            className="w-full border p-2 rounded"
          />

          <input
            name="category"
            value={form.category}
            onChange={handleChange}
            placeholder="Category"
            required
            className="w-full border p-2 rounded"
          />

          <input
            name="origin_country"
            value={form.origin_country}
            onChange={handleChange}
            placeholder="Origin Country"
            required
            className="w-full border p-2 rounded"
          />

          <input
            name="price_per_kg"
            type="number"
            step="0.01"
            value={form.price_per_kg}
            onChange={handleChange}
            placeholder="Price per kg"
            required
            className="w-full border p-2 rounded"
          />

          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
          >
            ✅ Update Product
          </button>
        </form>
      </div>
    </main>
  )
}