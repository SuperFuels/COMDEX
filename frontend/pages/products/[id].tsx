// pages/products/[id].tsx

import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import axios from 'axios'
import Link from 'next/link'
import QuoteModal from '@/components/QuoteModal'

interface Product {
  id: number
  title: string
  description: string
  price_per_kg: number
  origin_country: string
  category: string
  image_url: string
  owner_email: string
}

export default function ProductDetail() {
  const router = useRouter()
  const { id } = router.query
  const [product, setProduct] = useState<Product | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  useEffect(() => {
    if (!id) return

    async function fetchProduct() {
      try {
        const token = localStorage.getItem('token')
        const headers = token ? { Authorization: `Bearer ${token}` } : {}
        const response = await axios.get<Product>(
          `http://localhost:8000/products/${id}`,
          { headers }
        )
        console.log('💡 fetched product:', response.data)  // debug: should include owner_email
        setProduct(response.data)
      } catch (err) {
        console.error(err)
        setError('Could not load product.')
      } finally {
        setLoading(false)
      }
    }

    fetchProduct()
  }, [id])

  if (loading) return <p className="p-4 text-center">Loading…</p>
  if (error)   return <p className="p-4 text-red-500 text-center">{error}</p>
  if (!product) return <p className="p-4 text-center">Product not found.</p>

  return (
    <div className="max-w-3xl mx-auto p-6">
      <Link href="/" className="text-sm text-blue-500 hover:underline">
        ← Back to Marketplace
      </Link>

      <div className="mt-4 bg-white border rounded-lg p-6 shadow">
        <img
          src={
            product.image_url.startsWith('http')
              ? product.image_url
              : `http://localhost:8000${product.image_url}`
          }
          alt={product.title}
          className="w-full h-64 object-cover rounded mb-6"
          onError={(e) => {
            ;(e.currentTarget as HTMLImageElement).src = '/placeholder.jpg'
          }}
        />

        <h1 className="text-2xl font-bold mb-2">{product.title}</h1>
        <p className="text-gray-700 mb-4">{product.description}</p>

        <p className="mb-1">
          <strong>Origin:</strong> {product.origin_country}
        </p>
        <p className="mb-4">
          <strong>Category:</strong> {product.category}
        </p>
        <p className="text-xl font-semibold mb-6">
          ${product.price_per_kg}/kg
        </p>

        <button
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          onClick={() => setIsModalOpen(true)}
        >
          Generate Quote
        </button>
      </div>

      {isModalOpen && product && (
        <QuoteModal
          productId={product.id}
          productTitle={product.title}
          supplierEmail={product.owner_email}
          pricePerKg={product.price_per_kg}
          onClose={() => setIsModalOpen(false)}
        />
      )}
    </div>
  )
}

