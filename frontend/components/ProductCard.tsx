// frontend/components/ProductCard.tsx

import { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { StarIcon as SolidStar } from '@heroicons/react/24/solid'
import { StarIcon as OutlineStar } from '@heroicons/react/24/outline'

export interface ProductCardProps {
  id: number
  imageUrl: string
  pricePerTn: number          // price per metric tonne
  title: string
  rating: number              // 0–5
  reviewCount: number
  origin: string
  stockLocations: string[]    // e.g. ['Europe','Asia','Americas']
  tags: string[]              // e.g. ['Organic','Vegan']
  changePct: number           // e.g. +1.2 or -0.5
}

export default function ProductCard({
  id,
  imageUrl,
  pricePerTn,
  title,
  rating,
  reviewCount,
  origin,
  stockLocations,
  tags,
  changePct,
}: ProductCardProps) {
  // track current image src, fall back if load fails
  const [imgSrc, setImgSrc] = useState(imageUrl)

  // build star icons
  const stars = Array.from({ length: 5 }, (_, i) =>
    i < Math.round(rating) ? (
      <SolidStar key={i} className="w-4 h-4 text-yellow-500" />
    ) : (
      <OutlineStar key={i} className="w-4 h-4 text-gray-300" />
    )
  )

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm hover:shadow-md transition">
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
          <span className="text-sm text-gray-600">({reviewCount})</span>
        </div>

        {/* Origin & Stock */}
        <p className="text-sm text-gray-700">Origin: {origin}</p>
        <p className="text-sm text-gray-700">
          Stock in: {stockLocations.join(', ')}
        </p>

        {/* Tags */}
        <div className="flex flex-wrap gap-1">
          {tags.map(tag => (
            <span
              key={tag}
              className="text-xs bg-gray-100 text-gray-800 px-2 py-0.5 rounded-full"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Change % & Chart Link */}
        <div className="flex items-center justify-between">
          <span className={changePct >= 0 ? 'text-green-600' : 'text-red-600'}>
            {changePct >= 0 ? '↑' : '↓'} {Math.abs(changePct).toFixed(1)}%
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

