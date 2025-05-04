// frontend/pages/contracts/index.tsx

import { useEffect, useState } from 'react'
import axios from 'axios'
import Link from 'next/link'
import { Contract } from '../../types'

export default function ContractsPage() {
  const [contracts, setContracts] = useState<Contract[]>([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState<string | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('token')
    axios
      .get<Contract[]>('http://localhost:8000/contracts/', {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(res => setContracts(res.data))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load contracts'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p>Loading contracts…</p>
  if (error)   return <p className="text-red-600">Error: {error}</p>

  return (
    <div className="max-w-4xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">My Contracts</h1>
      <table className="min-w-full border-collapse">
        <thead>
          <tr className="bg-gray-200">
            <th className="border px-4 py-2">ID</th>
            <th className="border px-4 py-2">Prompt</th>
            <th className="border px-4 py-2">Status</th>
            <th className="border px-4 py-2">Created At</th>
            <th className="border px-4 py-2">View</th>
          </tr>
        </thead>
        <tbody>
          {contracts.map(c => (
            <tr key={c.id} className="odd:bg-white even:bg-gray-50">
              <td className="border px-4 py-2">{c.id}</td>
              <td className="border px-4 py-2">{c.prompt}</td>
              <td className="border px-4 py-2">{c.status}</td>
              <td className="border px-4 py-2">
                {new Date(c.created_at).toLocaleString()}
              </td>
              <td className="border px-4 py-2">
                <Link href={`/contracts/${c.id}`} className="text-blue-600 hover:underline">
                  View
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

