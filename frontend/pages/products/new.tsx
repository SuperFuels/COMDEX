// File: frontend/pages/products/new.tsx
"use client"

import { useState } from 'react'
import api from '@/lib/api'
import { useRouter } from 'next/router'
import useAuthRedirect from '@/hooks/useAuthRedirect'

export default function NewProduct() {
  useAuthRedirect('supplier') // ✅ Only suppliers can access

  const router = useRouter()

  const [form, setForm] = useState({
    title: '',
    description: '',
    price_per_kg: '',
    origin_country: '',
    category: '',
  })
  const [imageFile, setImageFile] = useState<File | null>(null)

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setImageFile(e.target.files[0])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const formData = new FormData()
    Object.entries(form).forEach(([key, value]) => {
      formData.append(key, value)
    })
    if (imageFile) formData.append('image', imageFile)

    try {
      await api.post('/products', formData)
      router.push('/supplier/dashboard')
    } catch (err) {
      console.error(err)
      alert('❌ Failed to create product')
    }
  }

  return (
    <main className="bg-gray-100 flex-1 flex items-center justify-center px-4 pt-0">
      <form
        onSubmit={handleSubmit}
        className="bg-white p-6 rounded shadow-md w-full max-w-lg space-y-4"
      >
        <h1 className="text-2xl font-bold text-center mb-2">📦 New Product</h1>

        <input
          type="text"
          name="title"
          placeholder="Title"
          value={form.title}
          onChange={handleChange}
          className="w-full border border-gray-300 rounded p-2"
          required
        />

        <textarea
          name="description"
          placeholder="Description"
          value={form.description}
          onChange={handleChange}
          className="w-full border border-gray-300 rounded p-2"
          rows={3}
          required
        />

        <input
          type="number"
          name="price_per_kg"
          placeholder="Price per kg (USD)"
          value={form.price_per_kg}
          onChange={handleChange}
          className="w-full border border-gray-300 rounded p-2"
          required
        />

        <input
          type="text"
          name="origin_country"
          placeholder="Country of Origin"
          value={form.origin_country}
          onChange={handleChange}
          className="w-full border border-gray-300 rounded p-2"
          required
        />

        <input
          type="text"
          name="category"
          placeholder="Category (e.g. Protein, Cocoa)"
          value={form.category}
          onChange={handleChange}
          className="w-full border border-gray-300 rounded p-2"
          required
        />

        <input
          type="file"
          accept="image/*"
          onChange={handleImageChange}
          className="w-full"
          required
        />

        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
        >
          Submit Product
        </button>
      </form>
    </main>
  )
}