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

  // Fetch the deal from your API
  const fetchDeal = async () => {
    if (!id) return
    setLoading(true)
    setError(null)

    try {
      const { data } = await api.get<Deal>(`/deals/${id}`)
      console.log('Loaded deal from API:', data)
      setDeal(data)
    } catch (err: any) {
      console.error(err)
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDeal()
  }, [id])

  // Buyer escrow step → mark confirmed on our server
  const handleEscrowSuccess = async () => {
    if (!id) return
    try {
      await api.put(`/deals/${id}/status`, { status: 'confirmed' })
      await fetchDeal()
    } catch (err: any) {
      console.error('Failed to update deal status:', err)
      alert(err.response?.data?.detail || 'Could not update deal status on server')
    }
  }

  // Supplier release step → call release endpoint
  const handleRelease = async () => {
    if (!id) return
    try {
      await api.post(`/deals/${id}/release`)
      await fetchDeal()
    } catch (err: any) {
      console.error('Release failed:', err)
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

      {/* 1) Buyer deposits GLU into escrow */}
      {deal.status === 'negotiation' && (
        <SwapPanel
          supplierAddress={deal.supplier_wallet_address}
          pricePerKg={deal.total_price / deal.quantity_kg}
          onSuccess={handleEscrowSuccess}
        />
      )}

      {/* 2) Supplier releases funds once GLU is locked */}
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

