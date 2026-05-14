// frontend/components/CreateProductForm.tsx
"use client"

import { useState } from 'react'
import api from '@/lib/api'

interface CreateProductFormProps {
  /** Called after a successful create; parent page can refresh or navigate */
  onSuccess: () => void
}

export default function CreateProductForm({ onSuccess }: CreateProductFormProps) {
  const [formData, setFormData] = useState({
    title: '',
    origin_country: '',
    category: '',
    description: '',
    price_per_kg: '',
    image: null as File | null,
  })
  const [error, setError] = useState('')

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, files } = e.target as any
    if (name === 'image' && files && files.length > 0) {
      setFormData((f) => ({ ...f, image: files[0] }))
    } else {
      setFormData((f) => ({ ...f, [name]: value }))
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
    if (formData.image) {
      data.append('image', formData.image)
    }

    try {
      await api.post('/products', data)
      // Notify parent that creation succeeded
      onSuccess()
    } catch (err: any) {
      setError(err.response?.data?.detail || '❌ Upload failed.')
    }
  }

  return (
    <div className="bg-white border border-black rounded-lg shadow-sm p-6 space-y-6">
      <h1 className="text-2xl font-semibold text-gray-800">Create Product</h1>

      {error && (
        <p className="text-red-600 text-sm border border-red-200 bg-red-50 rounded-md p-2">
          {error}
        </p>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Title */}
        <div className="space-y-1">
          <label htmlFor="title" className="block text-sm font-medium text-gray-700">
            Title
          </label>
          <input
            id="title"
            name="title"
            value={formData.title}
            onChange={handleChange}
            placeholder="e.g. Organic Whey Protein"
            className="
              block w-full
              px-4 py-2
              bg-white
              border border-black
              rounded-md
              text-gray-800 text-sm
              placeholder-gray-400
              focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent
            "
            required
          />
        </div>

        {/* Origin Country */}
        <div className="space-y-1">
          <label htmlFor="origin_country" className="block text-sm font-medium text-gray-700">
            Country of Origin
          </label>
          <input
            id="origin_country"
            name="origin_country"
            value={formData.origin_country}
            onChange={handleChange}
            placeholder="e.g. USA"
            className="
              block w-full
              px-4 py-2
              bg-white
              border border-black
              rounded-md
              text-gray-800 text-sm
              placeholder-gray-400
              focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent
            "
            required
          />
        </div>

        {/* Category */}
        <div className="space-y-1">
          <label htmlFor="category" className="block text-sm font-medium text-gray-700">
            Category (e.g. Whey)
          </label>
          <input
            id="category"
            name="category"
            value={formData.category}
            onChange={handleChange}
            placeholder="e.g. Whey Protein"
            className="
              block w-full
              px-4 py-2
              bg-white
              border border-black
              rounded-md
              text-gray-800 text-sm
              placeholder-gray-400
              focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent
            "
            required
          />
        </div>

        {/* Description */}
        <div className="space-y-1">
          <label htmlFor="description" className="block text-sm font-medium text-gray-700">
            Description
          </label>
          <textarea
            id="description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            rows={3}
            placeholder="Short description of your product"
            className="
              block w-full
              px-4 py-2
              bg-white
              border border-black
              rounded-md
              text-gray-800 text-sm
              placeholder-gray-400
              focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent
            "
            required
          />
        </div>

        {/* Price per KG */}
        <div className="space-y-1">
          <label htmlFor="price_per_kg" className="block text-sm font-medium text-gray-700">
            Price per KG (£)
          </label>
          <input
            id="price_per_kg"
            name="price_per_kg"
            type="number"
            step="0.01"
            value={formData.price_per_kg}
            onChange={handleChange}
            placeholder="e.g. 12.50"
            className="
              block w-full
              px-4 py-2
              bg-white
              border border-black
              rounded-md
              text-gray-800 text-sm
              placeholder-gray-400
              focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent
            "
            required
          />
        </div>

        {/* Image Upload */}
        <div className="space-y-1">
          <label htmlFor="image" className="block text-sm font-medium text-gray-700">
            Product Image
          </label>
          <input
            id="image"
            name="image"
            type="file"
            accept="image/*"
            onChange={handleChange}
            className="block w-full text-gray-700 text-sm"
            required
          />
        </div>

        {/* Submit Button */}
        <div>
          <button
            type="submit"
            className="
              inline-flex justify-center
              items-center
              px-6 py-2
              bg-blue-600 text-white
              font-medium text-sm
              rounded-md
              hover:bg-blue-700
              focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2
              transition
            "
          >
            Upload
          </button>
        </div>
      </form>
    </div>
  )
}