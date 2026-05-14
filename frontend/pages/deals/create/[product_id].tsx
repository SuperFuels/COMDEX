// File: frontend/pages/deals/create/[product_id].tsx
"use client"

import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import api from '@/lib/api'
import useAuthRedirect from '@/hooks/useAuthRedirect'

export default function CreateDealPage() {
  // Redirect non-buyers
  useAuthRedirect('buyer')

  const router = useRouter()
  const { product_id } = router.query as { product_id?: string }

  const [product, setProduct]       = useState<any>(null)
  const [quantityKg, setQuantityKg] = useState('')
  const [error, setError]           = useState('')
  const [loading, setLoading]       = useState(true)

  // Load product
  useEffect(() => {
    const loadProduct = async () => {
      const token = localStorage.getItem('token')
      if (!token || !product_id) return

      try {
        const res = await api.get(`/products/${product_id}`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        setProduct(res.data)
      } catch {
        setError('❌ Failed to load product data')
      } finally {
        setLoading(false)
      }
    }
    loadProduct()
  }, [product_id])

  // Submit deal
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    const token = localStorage.getItem('token')
    if (!token || !product_id) {
      setError('❌ Missing auth or product ID')
      return
    }
    try {
      await api.post(
        '/deals/',
        { product_id: Number(product_id), quantity_kg: Number(quantityKg) },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      router.push('/deals')
    } catch (err: any) {
      setError(err.response?.data?.detail || '❌ Deal creation failed')
    }
  }

  if (loading) return <p className="p-6 text-center">Loading product…</p>
  if (!product) return <p className="p-6 text-center text-red-600">{error || 'Product not found'}</p>

  return (
    <main className="pt-0"> {/* removed any top spacer */}
      <div className="min-h-screen bg-gray-100 flex flex-col">
        {/* no explicit <Navbar /> here; it's already in _app.tsx */}
        <div className="flex-1 max-w-2xl mx-auto p-6">
          <h1 className="text-2xl font-bold mb-4">Create Deal with Supplier</h1>
          {error && <p className="text-red-600 mb-4">{error}</p>}

          <div className="bg-white shadow p-4 rounded mb-6">
            <p><strong>Product:</strong> {product.title}</p>
            <p><strong>Price per KG:</strong> ${product.price_per_kg}</p>
            <p><strong>Supplier:</strong> {product.owner_email}</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="number"
              step="0.01"
              min="1"
              placeholder="Quantity (KG)"
              value={quantityKg}
              onChange={e => setQuantityKg(e.target.value)}
              className="w-full border border-gray-300 p-2 rounded"
              required
            />
            <button
              type="submit"
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              Submit Deal
            </button>
          </form>
        </div>
      </div>
    </main>
  )
}