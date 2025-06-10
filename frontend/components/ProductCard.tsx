// frontend/components/ProductCard.tsx
"use client"

import { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { StarIcon as SolidStar } from '@heroicons/react/24/solid'
import { StarIcon as OutlineStar } from '@heroicons/react/24/outline'

export interface ProductCardProps {
  product: {
    id: number
    image_url?: string
    price_per_kg: number
    title: string
    rating?: number      // 0–5 (you can default this)
    review_count?: number
    origin_country?: string
    stockLocations?: string[]
    tags?: string[]
    change_pct?: number
  }
  onClick?: () => void
}

export default function ProductCard({ product, onClick }: ProductCardProps) {
  const {
    id,
    image_url,
    price_per_kg,
    title,
    rating = 0,
    review_count = 0,
    origin_country = '—',
    stockLocations = [],
    tags = [],
    change_pct = 0,
  } = product

  // track current image src, fall back if load fails
  const [imgSrc, setImgSrc] = useState(image_url || '/placeholder.jpg')

  // build star icons
  const stars = Array.from({ length: 5 }, (_, i) =>
    i < Math.round(rating) ? (
      <SolidStar key={i} className="w-4 h-4 text-yellow-500" />
    ) : (
      <OutlineStar key={i} className="w-4 h-4 text-gray-300" />
    )
  )

  // convert price/kg to price/tonne
  const pricePerTn = price_per_kg * 1000

  return (
    <div
      onClick={onClick}
      className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition cursor-pointer"
    >
      {/* Image */}
      <div className="relative w-full h-48">
        <Image
          src={imgSrc}
          alt={title}
          fill
          style={{ objectFit: 'cover' }}
          onError={() => setImgSrc('/placeholder.jpg')}
        />
      </div>

      {/* Details */}
      <div className="p-4 space-y-2">
        {/* Price */}
        <p className="text-xs text-gray-500 uppercase">
          £{pricePerTn.toFixed(2)}/t
        </p>

        {/* Title */}
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>

        {/* Rating */}
        <div className="flex items-center space-x-1">
          {stars}
          <span className="text-sm text-gray-600">({review_count})</span>
        </div>

        {/* Origin & Stock */}
        <p className="text-sm text-gray-700">Origin: {origin_country}</p>
        {stockLocations.length > 0 && (
          <p className="text-sm text-gray-700">
            Stock in: {stockLocations.join(', ')}
          </p>
        )}

        {/* Tags */}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {tags.map((tag) => (
              <span
                key={tag}
                className="text-xs bg-gray-100 text-gray-800 px-2 py-0.5 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Change % & Chart Link */}
        <div className="flex items-center justify-between">
          <span className={change_pct >= 0 ? 'text-green-600' : 'text-red-600'}>
            {change_pct >= 0 ? '↑' : '↓'} {Math.abs(change_pct).toFixed(1)}%
          </span>
          <Link
            href={`/products/${id}/chart`}
            className="text-sm font-medium text-primary hover:underline"
          >
            Chart →
          </Link>
        </div>
      </div>
    </div>
  )
}