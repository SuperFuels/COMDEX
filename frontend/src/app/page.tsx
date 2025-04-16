'use client'

import { useEffect, useState } from 'react'
import api from '../lib/api'
import ProductCard from '../components/ProductCard';

export default function HomePage() {
  const [products, setProducts] = useState([])

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const response = await api.get('/products')
        setProducts(response)
      } catch (error) {
        console.error('Error fetching products:', error)
      }
    }

    fetchProducts()
  }, [])

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Available Products</h1>
      {products.length === 0 ? (
        <p>No products found.</p>
      ) : (
        products.map((product: any, index: number) => (
          <ProductCard key={index} {...product} />
        ))
      )}
    </div>
  )
}

