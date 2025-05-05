import { useEffect, useState } from 'react'
import Link from 'next/link'
import axios from 'axios'
import { Deal } from '../../types'

export default function DealsPage() {
  const [deals, setDeals]       = useState<Deal[]>([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState<string | null>(null)

  const fetchDeals = () => {
    setLoading(true)
    setError(null)
    const token = localStorage.getItem('token')
    axios
      .get<Deal[]>('http://localhost:8000/deals/', {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => setDeals(res.data))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load deals'))
      .finally(() => setLoading(false))
  }

  const changeStatus = (id: number, nextStatus: 'confirmed' | 'completed') => {
    const token = localStorage.getItem('token')
    axios
      .put(
        `http://localhost:8000/deals/${id}/status`,
        { status: nextStatus },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      .then(() => {
        alert(`Status updated to ${nextStatus}`)
        fetchDeals()
      })
      .catch(err => {
        alert(err.response?.data?.detail || 'Failed to update status')
      })
  }

  useEffect(() => {
    fetchDeals()
  }, [])

  if (loading) return <p>Loading deals…</p>
  if (error)   return <p className="text-red-600">Error: {error}</p>
  if (deals.length === 0) return <p>No deals found.</p>

  return (
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
          {deals.map(d => {
            const next =
              d.status === 'negotiation'
                ? 'confirmed'
                : d.status === 'confirmed'
                  ? 'completed'
                  : null

            return (
              <tr key={d.id} className="odd:bg-white even:bg-gray-50">
                <td className="border px-4 py-2">{d.id}</td>
                <td className="border px-4 py-2">{d.product_title}</td>
                <td className="border px-4 py-2">{d.status}</td>
                <td className="border px-4 py-2">
                  {new Date(d.created_at).toLocaleString()}
                </td>
                <td className="border px-4 py-2">
                  {next && (
                    <button
                      className="bg-green-500 text-white px-2 py-1 rounded mr-2"
                      onClick={() => changeStatus(d.id, next as any)}
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
  )
}

