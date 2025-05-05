import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import axios from 'axios'
import { Contract } from '../../../types'

export default function ContractDetailPage() {
  const router = useRouter()
  const { id } = router.query as { id?: string }
  const [contract, setContract] = useState<Contract | null>(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState<string | null>(null)

  useEffect(() => {
    if (!id) return setLoading(false)
    setLoading(true)
    setError(null)
    const token = localStorage.getItem('token')
    axios
      .get<Contract>(`http://localhost:8000/contracts/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then(res => setContract(res.data))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load contract'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <p>Loading contract…</p>
  if (error)   return <p className="text-red-600">Error: {error}</p>
  if (!contract) return <p>Contract not found</p>

  return (
    <div className="max-w-3xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Contract #{contract.id}</h1>
      <p><strong>Prompt:</strong> {contract.prompt}</p>
      <p><strong>Status:</strong> {contract.status}</p>
      <p>
        <strong>Created at:</strong>{' '}
        {new Date(contract.created_at).toLocaleString()}
      </p>

      <div className="mt-6 p-4 bg-gray-50 border rounded">
        <h2 className="text-xl font-semibold mb-2">Generated Contract</h2>
        <div
          className="prose"
          dangerouslySetInnerHTML={{ __html: contract.generated_contract }}
        />
      </div>

      <a
        href={`http://localhost:8000/contracts/${contract.id}/pdf`}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-4 inline-block px-4 py-2 bg-blue-600 text-white rounded"
      >
        Download PDF
      </a>
    </div>
  )
}

