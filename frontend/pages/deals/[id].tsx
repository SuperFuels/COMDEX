// File: frontend/pages/deals/[id].tsx
"use client"

import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import api from '@/lib/api'
import SwapPanel from '@/components/SwapPanel'

/**
 * Locally define a minimal Deal interface so we no longer
 * need to import from “@/types” (which did not exist).
 */
interface Deal {
  id: number
  product_title: string
  quantity_kg: number
  total_price: number
  status: 'negotiation' | 'confirmed' | string
  created_at: string
  supplier_wallet_address?: string
}

export default function DealDetailPage() {
  const router = useRouter()
  const { id } = router.query as { id?: string }

  const [deal, setDeal]       = useState<Deal | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  // Fetch (or re‐fetch) the deal whenever `id` becomes available
  useEffect(() => {
    const fetchDeal = async () => {
      if (!id) return
      setLoading(true)
      setError(null)
      try {
        const { data } = await api.get<Deal>(`/deals/${id}`)
        setDeal(data)
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchDeal()
  }, [id])

  const handleEscrowSuccess = async () => {
    if (!id) return
    try {
      await api.put(`/deals/${id}/status`, { status: 'confirmed' })
      const { data } = await api.get<Deal>(`/deals/${id}`)
      setDeal(data)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Could not confirm escrow')
    }
  }

  const handleRelease = async () => {
    if (!id) return
    try {
      await api.post(`/deals/${id}/release`)
      const { data } = await api.get<Deal>(`/deals/${id}`)
      setDeal(data)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Release failed')
    }
  }

  if (loading) return <p className="p-6 text-center">Loading…</p>
  if (error)   return <p className="p-6 text-center text-red-600">{error}</p>
  if (!deal)   return <p className="p-6 text-center">Deal not found</p>

  return (
    <main className="pt-0"> {/* cancel the global pt-16 here */}
      <div className="max-w-xl mx-auto p-4">
        <h1 className="text-2xl font-bold mb-4">Deal #{deal.id}</h1>
        <p><strong>Product:</strong> {deal.product_title}</p>
        <p><strong>Quantity:</strong> {deal.quantity_kg} kg</p>
        <p><strong>Total:</strong> ${deal.total_price}</p>
        <p><strong>Status:</strong> {deal.status}</p>
        <p>
          <strong>Created at:</strong>{' '}
          {new Date(deal.created_at).toLocaleString()}
        </p>

        {deal.status === 'negotiation' && (
          <SwapPanel
            supplierAddress={deal.supplier_wallet_address!}
            pricePerKg={deal.total_price / deal.quantity_kg}
            onSuccess={handleEscrowSuccess}
          />
        )}

        {deal.status === 'confirmed' && (
          <button
            className="mt-4 bg-red-500 text-white px-4 py-2 rounded"
            onClick={handleRelease}
          >
            Release Funds
          </button>
        )}
      </div>
    </main>
  )
}