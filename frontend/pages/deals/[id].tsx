// pages/deals/[id].tsx

import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import axios from 'axios'
import SwapPanel from '../../components/SwapPanel'
import { Deal } from '../../types'

export default function DealDetailPage() {
  const router = useRouter()
  const { id } = router.query as { id?: string }
  const [deal, setDeal]       = useState<Deal | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError]     = useState<string | null>(null)

  const fetchDeal = () => {
    if (!id) return
    setLoading(true)
    setError(null)
    const token = localStorage.getItem('token')
    axios
      .get<Deal>(`${process.env.NEXT_PUBLIC_API_URL}/deals/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then(res => setDeal(res.data))
      .catch(err => {
        setError(err.response?.data?.detail || err.message)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchDeal()
  }, [id])

  if (loading) return <p>Loading…</p>
  if (error)   return <p className="text-red-600">{error}</p>
  if (!deal)   return <p>Deal not found</p>

  return (
    <div className="max-w-xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Deal #{deal.id}</h1>
      <p><strong>Product:</strong> {deal.product_title}</p>
      <p><strong>Quantity:</strong> {deal.quantity_kg} kg</p>
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
          onSuccess={fetchDeal}
        />
      )}

      {/* 2) Supplier releases funds once GLU is locked */}
      {deal.status === 'released' && (
        <button
          className="mt-4 bg-red-500 text-white px-4 py-2 rounded"
          onClick={async () => {
            const token = localStorage.getItem('token')
            try {
              await axios.post(
                `${process.env.NEXT_PUBLIC_API_URL}/deals/${id}/release`,
                {},
                { headers: { Authorization: `Bearer ${token}` } }
              )
              fetchDeal()
            } catch (err: any) {
              console.error(err)
              alert(err.response?.data?.detail || 'Release failed')
            }
          }}
        >
          Release Funds
        </button>
      )}
    </div>
  )
}

