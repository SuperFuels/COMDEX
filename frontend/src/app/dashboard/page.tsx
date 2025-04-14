// src/app/dashboard/page.tsx
'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import ProductCard from '@/components/ProductCard'

export default function DashboardPage() {
  const [products, setProducts] = useState([])

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) return

    api.get('/products/', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
    .then(res => setProducts(res.data))
    .catch(err => console.error('Failed to fetch products', err))
  }, [])

  return (
    <main className="p-8 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">📦 Your Listings</h1>
      {products.length > 0 ? (
        products.map((product: any) => (
          <ProductCard key={product.id} product={product} />
        ))
      ) : (
        <p className="text-gray-500">You haven’t listed any products yet.</p>
      )}
    </main>
  )
}

