"use client"
import { useState } from 'react'
import api from '@/lib/api'

export default function InventoryCreate({ onCreated }: { onCreated: () => void }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [price, setPrice] = useState('')
  const [origin, setOrigin] = useState('')
  const [category, setCategory] = useState('')
  const [imageFile, setImageFile] = useState<File|null>(null)
  const [error, setError] = useState<string|null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!imageFile) return setError('Select an image')
    const fd = new FormData()
    fd.append('title', title)
    fd.append('description', description)
    fd.append('price_per_kg', price)
    fd.append('origin_country', origin)
    fd.append('category', category)
    fd.append('image', imageFile)
    try {
      await api.post('products', fd)
      onCreated()
      setTitle(''); setDescription(''); setPrice(''); setOrigin(''); setCategory(''); setImageFile(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Create failed')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <p className="text-red-600">{error}</p>}
      <input name="title" value={title} onChange={e=>setTitle(e.currentTarget.value)} placeholder="Title" required className="w-full p-2 border rounded"/>
      <input name="price_per_kg" value={price} onChange={e=>setPrice(e.currentTarget.value)} placeholder="Price per kg" required className="w-full p-2 border rounded"/>
      <input name="origin_country" value={origin} onChange={e=>setOrigin(e.currentTarget.value)} placeholder="Origin country" className="w-full p-2 border rounded"/>
      <input name="category" value={category} onChange={e=>setCategory(e.currentTarget.value)} placeholder="Category" className="w-full p-2 border rounded"/>
      <textarea name="description" value={description} onChange={e=>setDescription(e.currentTarget.value)} placeholder="Description" className="w-full p-2 border rounded"/>
      <input type="file" accept="image/*" onChange={e=>setImageFile(e.target.files?.[0]||null)} required className="w-full"/>
      <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded">Create</button>
    </form>
  )
}
