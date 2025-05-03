import React from 'react'
import Link from 'next/link'

interface ProductProps {
  id: number
  title: string
  description: string
  price_per_kg: number
  origin_country: string
  image_url: string
}

const ProductCard: React.FC<ProductProps> = ({
  id,
  title,
  description,
  price_per_kg,
  origin_country,
  image_url,
}) => {
  return (
    <div className="border rounded shadow p-4 flex flex-col">
      <img
        src={image_url}
        alt={title}
        className="h-40 w-full object-cover mb-2 rounded"
      />
      <h2 className="text-xl font-bold">{title}</h2>
      <p className="text-gray-600 text-sm mb-2">{origin_country}</p>
      <p className="text-gray-800 flex-grow">{description}</p>
      <p className="font-bold mt-2">${price_per_kg}/kg</p>

      {/* VIEW PRODUCT BUTTON */}
      <Link href={`/products/${id}`}>
        <a className="mt-4 inline-block bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded text-center">
          View Product
        </a>
      </Link>
    </div>
  )
}

export default ProductCard

