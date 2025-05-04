// frontend/pages/products/[id].tsx

import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import axios from 'axios'
import SwapPanel from '../../components/SwapPanel'

interface Product {
  id: number
  title: string
  description: string
  origin_country: string
  price_per_kg: number
  image_url: string
  owner_email: string
  change_pct: number    // ← new
  rating: number        // ← new
}

export default function ProductDetail() {
  const router = useRouter()
  const { id } = router.query as { id?: string }
  const [prod, setProd] = useState<Product | null>(null)
  const [loading, setLoading] = useState(true)
  const [showSwap, setShowSwap] = useState(false)

  useEffect(() => {
    if (!id) return
    const token = localStorage.getItem('token')
    axios
      .get<Product>(`http://localhost:8000/products/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(r => setProd(r.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <p>Loading…</p>
  if (!prod)   return <p>Product not found</p>

  return (
    <div className="max-w-3xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-2">{prod.title}</h1>
      <img
        src={
          prod.image_url.startsWith('http')
            ? prod.image_url
            : `http://localhost:8000${prod.image_url}`
        }
        alt={prod.title}
        className="w-full h-64 object-cover rounded mb-4"
      />
      <p className="mb-2">{prod.description}</p>
      <p className="mb-1">
        <strong>Origin:</strong> {prod.origin_country}
      </p>
      <p className="mb-1">
        <strong>Price per kg:</strong> ${prod.price_per_kg.toFixed(2)}
      </p>
      <p className="mb-1">
        <strong>Change % (24h):</strong> {(prod.change_pct * 100).toFixed(2)}%
      </p>
      <p className="mb-4">
        <strong>Rating:</strong> {prod.rating.toFixed(1)}/10
      </p>

      <button
        onClick={() => setShowSwap(s => !s)}
        className="bg-blue-600 text-white px-4 py-2 rounded mb-4"
      >
        {showSwap ? 'Cancel' : 'Get Quote'}
      </button>

      {showSwap && (
        <div className="mt-4">
          <SwapPanel
            productId={prod.id}
            pricePerKg={prod.price_per_kg}
            onSuccess={() => {
              alert('Deal created!')
              setShowSwap(false)
              router.push('/deals')
            }}
          />
        </div>
      )}
    </div>
  )
}

