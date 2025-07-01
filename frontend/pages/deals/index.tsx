// frontend/pages/deals/index.tsx
"use client"

import { useEffect, useState } from 'react'
import Link from 'next/link'
import api from '@/lib/api'
import { Deal } from '@/types'

export default function DealsPage() {
  const [deals, setDeals]     = useState<Deal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  // fetch all deals
  const fetchDeals = async () => {
    setLoading(true)
    setError(null)

    const token = localStorage.getItem('token')
    if (!token) {
      setError('Not authenticated')
      setLoading(false)
      return
    }

    try {
      const res = await api.get<Deal[]>('/deals/', {
        headers: { Authorization: `Bearer ${token}` },
      })
      setDeals(res.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load deals')
    } finally {
      setLoading(false)
    }
  }

  // advance status from negotiation → confirmed → completed
  const changeStatus = async (
    id: number,
    nextStatus: 'confirmed' | 'completed'
  ) => {
    const token = localStorage.getItem('token')
    if (!token) {
      alert('Not authenticated')
      return
    }

    try {
      await api.put(
        `/deals/${id}/status`,
        { status: nextStatus },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      alert(`Status updated to ${nextStatus}`)
      await fetchDeals()
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update status')
    }
  }

  useEffect(() => {
    fetchDeals()
  }, [])

  if (loading) return <p className="p-6">Loading deals…</p>
  if (error)   return <p className="p-6 text-red-600">Error: {error}</p>
  if (deals.length === 0) return <p className="p-6">No deals found.</p>

  return (
    <main className="pt-0"> {/* override the global pt-16 */}
      <div className="max-w-4xl mx-auto p-4">
        <h1 className="text-2xl font-bold mb-4">My Deals</h1>
        <table className="min-w-full border-collapse">
          <thead>
            <tr className="bg-gray-200">
              <th className="border px-4 py-2">ID</th>
              <th className="border px-4 py-2">Product</th>
              <th className="border px-4 py-2">Status</th>
              <th className="border px-4 py-2">Created At</th>
              <th className="border px-4 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {deals.map((d) => {
              const next =
                d.status === 'negotiation'
                  ? 'confirmed'
                  : d.status === 'confirmed'
                  ? 'completed'
                  : null

              return (
                <tr
                  key={d.id}
                  className="odd:bg-white even:bg-gray-50 hover:bg-gray-100"
                >
                  <td className="border px-4 py-2">{d.id}</td>
                  <td className="border px-4 py-2">{d.product_title}</td>
                  <td className="border px-4 py-2">{d.status}</td>
                  <td className="border px-4 py-2">
                    {new Date(d.created_at).toLocaleString()}
                  </td>
                  <td className="border px-4 py-2 space-x-2">
                    {next && (
                      <button
                        className="bg-green-500 text-white px-2 py-1 rounded"
                        onClick={() =>
                          changeStatus(d.id, next as 'confirmed' | 'completed')
                        }
                      >
                        {d.status === 'negotiation' ? 'Confirm' : 'Complete'}
                      </button>
                    )}
                    <Link
                      href={`/deals/${d.id}`}
                      className="text-blue-600 hover:underline"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </main>
  )
}