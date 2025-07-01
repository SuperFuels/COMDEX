"use client"
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

export default function InventoryEdit({
  products,
  onEdited,
}: {
  products: Product[]
  onEdited: () => void
}) {
  const [editId, setEditId] = useState<number | ''>('')
  const [form, setForm] = useState({
    title: '',
    description: '',
    price_per_kg: '',
    origin_country: '',
    category: '',
  })
  const [error, setError] = useState<string | null>(null)

  // Prefill when selection changes
  useEffect(() => {
    if (editId === '' || !products) return
    const p = products.find(p => p.id === editId)!
    setForm({
      title: p.title,
      description: p.description || '',
      price_per_kg: String(p.price_per_kg),
      origin_country: p.origin_country || '',
      category: p.category || '',
    })
  }, [editId, products])

  // Submit update
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (editId === '') return
    setError(null)
    try {
      await api.put(`products/${editId}`, {
        title: form.title,
        description: form.description,
        price_per_kg: parseFloat(form.price_per_kg),
        origin_country: form.origin_country,
        category: form.category,
      })
      setEditId('')
      onEdited()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Update failed')
    }
  }

  return (
    <div className="space-y-4">
      {error && <p className="text-red-600">{error}</p>}

      <label className="block">
        <span className="font-semibold">Select product to edit:</span>
        <select
          className="mt-1 p-2 border rounded w-full"
          value={editId}
          onChange={e => setEditId(Number(e.target.value))}
        >
          <option value="" disabled>-- pick one --</option>
          {products.map(p => (
            <option key={p.id} value={p.id}>
              {p.title} (ID: {p.id})
            </option>
          ))}
        </select>
      </label>

      {editId !== '' && (
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            name="title"
            value={form.title}
            onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
            placeholder="Title"
            required
            className="w-full p-2 border rounded"
          />
          <input
            name="price_per_kg"
            type="number"
            value={form.price_per_kg}
            onChange={e => setForm(f => ({ ...f, price_per_kg: e.target.value }))}
            placeholder="Price per kg"
            required
            className="w-full p-2 border rounded"
          />
          <input
            name="origin_country"
            value={form.origin_country}
            onChange={e => setForm(f => ({ ...f, origin_country: e.target.value }))}
            placeholder="Origin country"
            className="w-full p-2 border rounded"
          />
          <input
            name="category"
            value={form.category}
            onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
            placeholder="Category"
            className="w-full p-2 border rounded"
          />
          <textarea
            name="description"
            value={form.description}
            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            placeholder="Description"
            className="w-full p-2 border rounded"
          />
          <button type="submit" className="px-4 py-2 bg-green-600 text-white rounded">
            Save Changes
          </button>
        </form>
      )}
    </div>
  )
}
