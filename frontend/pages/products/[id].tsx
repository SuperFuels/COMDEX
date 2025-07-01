// File: frontend/pages/products/[id].tsx
"use client"

import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import api from '@/lib/api'
import Image from 'next/image'
import Link from 'next/link'
import { StarIcon as SolidStar } from '@heroicons/react/24/solid'
import { StarIcon as OutlineStar } from '@heroicons/react/24/outline'

interface Product {
  id: number
  title: string
  description: string
  price_per_kg: number
  origin_country: string
  change_pct: number
  rating: number       // 0–5
  review_count: number
  image_url?: string   // single image path: "/uploaded_images/xxx.png"
  category: string
}

export default function ProductDetailPage() {
  const router = useRouter()
  const { id } = router.query as { id?: string }
  const [product, setProduct] = useState<Product | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [mainImage, setMainImage] = useState<string | null>(null)

  const getImageSrc = (path?: string) => {
    if (!path) return '/placeholder.jpg'
    const base = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '') || ''
    return `${base}${path}`
  }

  useEffect(() => {
    if (!id) return
    setLoading(true)
    api
      .get<Product>(`/products/${id}`)
      .then(({ data }) => {
        setProduct(data)
        setMainImage(getImageSrc(data.image_url))
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return <p className="p-8 text-center">Loading product…</p>
  }
  if (error || !product) {
    return <p className="p-8 text-center text-red-500">Failed to load product.</p>
  }

  const stars = Array.from({ length: 5 }, (_, i) =>
    i < Math.round(product.rating) ? (
      <SolidStar key={i} className="w-5 h-5 text-yellow-500" />
    ) : (
      <OutlineStar key={i} className="w-5 h-5 text-gray-300" />
    )
  )

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto bg-white shadow rounded-lg overflow-hidden">
        {/* Breadcrumb */}
        <nav className="px-6 py-3 text-sm text-gray-600" aria-label="Breadcrumb">
          <ol className="flex space-x-2">
            <li>
              <Link href="/" legacyBehavior>
                <a className="hover:underline">Home</a>
              </Link>
              <span className="mx-2">/</span>
            </li>
            <li>
              <Link href={`/category/${product.category}`} legacyBehavior>
                <a className="hover:underline">{product.category}</a>
              </Link>
              <span className="mx-2">/</span>
            </li>
            <li className="text-gray-800">{product.title}</li>
          </ol>
        </nav>

        <div className="px-6 pb-8 grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Image */}
          <div className="lg:col-span-6">
            <div className="border rounded overflow-hidden">
              <Image
                src={mainImage || '/placeholder.jpg'}
                alt={product.title}
                width={600}
                height={400}
                objectFit="contain"
                className="bg-white"
              />
            </div>
          </div>

          {/* Product Info */}
          <div className="lg:col-span-4 space-y-4">
            <h1 className="text-2xl font-bold text-gray-900">{product.title}</h1>
            <p className="text-gray-700">{product.description}</p>

            {/* Rating */}
            <div className="flex items-center space-x-2">
              <div className="flex">{stars}</div>
              <span className="text-sm text-gray-600">
                {product.review_count} review{product.review_count !== 1 && 's'}
              </span>
            </div>

            {/* Price */}
            <div className="flex items-baseline space-x-2">
              <span className="text-3xl font-extrabold text-gray-900">
                £{(product.price_per_kg * 1000).toFixed(2)}/t
              </span>
              <span
                className={`text-sm font-medium ${
                  product.change_pct >= 0 ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {product.change_pct >= 0 ? '↑' : '↓'}{' '}
                {Math.abs(product.change_pct).toFixed(2)}%
              </span>
            </div>

            {/* Actions */}
            <div className="flex flex-col space-y-2">
              <button
                onClick={() => router.push(`/contracts/new?product=${product.id}`)}
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded"
              >
                Create Contract
              </button>
              <button
                onClick={() => router.push(`/products/${product.id}/sample`)}
                className="w-full py-3 bg-gray-200 hover:bg-gray-300 text-gray-800 rounded"
              >
                Order Sample
              </button>
              <button
                onClick={() => router.push(`/products/${product.id}/zoom`)}
                className="w-full py-3 bg-green-600 hover:bg-green-700 text-white rounded"
              >
                Setup Zoom Call
              </button>
            </div>
          </div>

          {/* Sidebar */}
          <aside className="lg:col-span-2 space-y-4">
            <div className="bg-gray-50 p-4 rounded border text-center">
              <p className="text-sm text-gray-600">Origin</p>
              <p className="font-medium text-gray-900">{product.origin_country}</p>
            </div>
            <div className="bg-gray-50 p-4 rounded border text-center">
              <p className="text-sm text-gray-600">Category</p>
              <p className="font-medium text-gray-900">{product.category}</p>
            </div>
            <div className="bg-gray-50 p-4 rounded border text-center">
              <p className="text-sm text-gray-600">Rating</p>
              <p className="font-medium text-gray-900">
                {product.rating.toFixed(1)}/5
              </p>
            </div>
          </aside>
        </div>
      </div>
    </div>
  )
}