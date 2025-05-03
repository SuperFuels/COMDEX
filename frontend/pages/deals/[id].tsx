import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import axios from 'axios'

interface Deal {
  id: number
  buyer_email: string
  supplier_email: string
  product_title: string
  quantity_kg: number
  total_price: number
  status: string
  created_at: string
}

export default function DealDetailPage() {
  const router = useRouter()
  const { id } = router.query
  const [deal, setDeal] = useState<Deal | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    axios
      .get<Deal>(`http://localhost:8000/deals/${id}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      })
      .then(res => setDeal(res.data))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load deal'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <p>Loading deal…</p>
  if (error)   return <p className="text-red-600">Error: {error}</p>
  if (!deal)   return <p>Deal not found</p>

  return (
    <div className="max-w-xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Deal #{deal.id}</h1>
      <p><strong>Product:</strong> {deal.product_title}</p>
      <p><strong>Buyer:</strong> {deal.buyer_email}</p>
      <p><strong>Supplier:</strong> {deal.supplier_email}</p>
      <p><strong>Quantity:</strong> {deal.quantity_kg} kg</p>
      <p><strong>Total Price:</strong> ${deal.total_price}</p>
      <p><strong>Status:</strong> {deal.status}</p>
      <p><strong>Created at:</strong> {new Date(deal.created_at).toLocaleString()}</p>
    </div>
  )
}

