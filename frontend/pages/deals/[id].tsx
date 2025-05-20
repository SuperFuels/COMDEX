// frontend/pages/deals/[id].tsx

import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import api from '@/lib/api'
import SwapPanel from '@/components/SwapPanel'
import { Deal } from '@/types'

export default function DealDetailPage() {
  const router = useRouter()
  const { id } = router.query as { id?: string }

  const [deal, setDeal]       = useState<Deal | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  // fetch / refetch the deal
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
      // refetch to get updated status
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
      // refetch to get updated status
      const { data } = await api.get<Deal>(`/deals/${id}`)
      setDeal(data)
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Release failed')
    }
  }

  if (loading) return <p>Loading…</p>
  if (error)   return <p className="text-red-600">{error}</p>
  if (!deal)   return <p>Deal not found</p>

  return (
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
  )
}

