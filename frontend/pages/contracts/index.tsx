"use client"

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import Link from 'next/link'
import { Contract } from '../../types'

export default function ContractsPage() {
  const [contracts, setContracts] = useState<Contract[]>([])
  const [loading, setLoading]     = useState<boolean>(true)
  const [error, setError]         = useState<string | null>(null)

  useEffect(() => {
    const fetchContracts = async () => {
      setLoading(true)
      setError(null)

      const token = localStorage.getItem('token')
      if (!token) {
        setError('Not authenticated')
        setLoading(false)
        return
      }

      try {
        const res = await api.get<Contract[]>('/contracts/', {
          headers: { Authorization: `Bearer ${token}` },
        })
        setContracts(res.data)
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load contracts')
      } finally {
        setLoading(false)
      }
    }

    fetchContracts()
  }, [])

  if (loading) {
    return <p className="text-center py-8">Loading contracts…</p>
  }

  if (error) {
    return <p className="text-red-600 text-center py-8">Error: {error}</p>
  }

  if (contracts.length === 0) {
    return <p className="text-center py-8">No contracts found.</p>
  }

  return (
    // cancel out the global pt-16 so we sit flush under the navbar
    <main className="mt-[-4rem] pt-0">
      <div className="max-w-4xl mx-auto p-4">
        <h1 className="text-2xl font-bold mb-4">My Contracts</h1>
        <table className="min-w-full border-collapse">
          <thead>
            <tr className="bg-gray-200">
              <th className="border px-4 py-2 text-left">ID</th>
              <th className="border px-4 py-2 text-left">Prompt</th>
              <th className="border px-4 py-2 text-left">Status</th>
              <th className="border px-4 py-2 text-left">Created At</th>
              <th className="border px-4 py-2 text-left">View</th>
            </tr>
          </thead>
          <tbody>
            {contracts.map((c) => (
              <tr key={c.id} className="odd:bg-white even:bg-gray-50">
                <td className="border px-4 py-2">{c.id}</td>
                <td className="border px-4 py-2">{c.prompt}</td>
                <td className="border px-4 py-2">{c.status}</td>
                <td className="border px-4 py-2">
                  {new Date(c.created_at).toLocaleString()}
                </td>
                <td className="border px-4 py-2">
                  <Link
                    href={`/contracts/${c.id}`}
                    className="text-blue-600 hover:underline"
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  )
}
