// frontend/pages/contracts/[id].tsx

import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import axios from 'axios'
import { Contract } from '../../types'

export default function ContractDetail() {
  const router = useRouter()
  const { id } = router.query as { id?: string }
  const [contract, setContract] = useState<Contract|null>(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState<string|null>(null)

  useEffect(() => {
    console.log('ContractDetail: id =', id)
    if (!id) {
      setLoading(false)
      return
    }
    setLoading(true)
    const token = localStorage.getItem('token')
    axios
      .get<Contract>(`http://localhost:8000/contracts/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(r => setContract(r.data))
      .catch(err => setError(err.response?.data?.detail || 'Failed to load contract'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading)  return <p>Loading contract…</p>
  if (error)    return <p className="text-red-600">{error}</p>
  if (!contract) return <p>Contract not found</p>

  return (
    <div className="max-w-2xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-2">Contract #{contract.id}</h1>
      <p className="italic mb-4">Status: {contract.status}</p>
      <div
        className="prose mb-6"
        dangerouslySetInnerHTML={{ __html: contract.generated_contract }}
      />
      <a
        href={`http://localhost:8000/contracts/${contract.id}/pdf`}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-block mt-4 px-4 py-2 bg-green-600 text-white rounded"
      >
        Download Contract PDF
      </a>
    </div>
  )
}

