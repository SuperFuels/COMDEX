// File: frontend/pages/products/create.tsx
"use client"

import { useEffect, useState } from 'react'
import { useRouter } from 'next/router'
import useAuthRedirect from '@/hooks/useAuthRedirect'
import api from '@/lib/api'

export default function CreateProductPage() {
  const router = useRouter()
  // will redirect to /login or / if not a supplier
  useAuthRedirect('supplier')

  const [formData, setFormData] = useState({
    title: '',
    origin_country: '',
    category: '',
    description: '',
    price_per_kg: '',
    image: null as File | null,
  })
  const [error, setError] = useState('')

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, files } = e.target
    if (name === 'image' && files) {
      setFormData(f => ({ ...f, image: files[0] }))
    } else {
      setFormData(f => ({ ...f, [name]: value }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    const data = new FormData()
    data.append('title', formData.title)
    data.append('origin_country', formData.origin_country)
    data.append('category', formData.category)
    data.append('description', formData.description)
    data.append('price_per_kg', formData.price_per_kg)
    if (formData.image) data.append('image', formData.image)

    try {
      // POST to /products (not /products/create)
      await api.post('/products', data)
      router.push('/supplier/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || '❌ Upload failed.')
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Upload New Product</h1>
      {error && <p className="text-red-600 mb-4">{error}</p>}

      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          name="title"
          placeholder="Title"
          onChange={handleChange}
          className="w-full border border-gray-300 p-2 rounded"
          required
        />

        <input
          name="origin_country"
          placeholder="Country of Origin"
          onChange={handleChange}
          className="w-full border border-gray-300 p-2 rounded"
          required
        />

        <input
          name="category"
          placeholder="Category (e.g. whey)"
          onChange={handleChange}
          className="w-full border border-gray-300 p-2 rounded"
          required
        />

        <input
          name="description"
          placeholder="Description"
          onChange={handleChange}
          className="w-full border border-gray-300 p-2 rounded"
          required
        />

        <input
          name="price_per_kg"
          type="number"
          step="0.01"
          placeholder="Price per KG"
          onChange={handleChange}
          className="w-full border border-gray-300 p-2 rounded"
          required
        />

        <input
          name="image"
          type="file"
          accept="image/*"
          onChange={handleChange}
          className="w-full"
          required
        />

        <button
          type="submit"
          className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Upload
        </button>
      </form>
    </main>
  )
}