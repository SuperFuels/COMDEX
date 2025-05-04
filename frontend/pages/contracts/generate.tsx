// frontend/pages/contracts/generate.tsx

import { useState } from 'react'
import { useRouter } from 'next/router'
import axios from 'axios'

export default function ContractGeneratePage() {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState<string | null>(null)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim()) {
      setError('Please enter a prompt')
      return
    }
    setLoading(true)
    setError(null)

    try {
      const token = localStorage.getItem('token')
      const res = await axios.post(
        'http://localhost:8000/contracts/generate',
        { prompt },
        { headers: { Authorization: `Bearer ${token}` } }
      )
      const { id } = res.data
      router.push(`/contracts/${id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate contract')
      setLoading(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Draft a Contract</h1>
      {error && <p className="text-red-600 mb-2">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. Sell my white Peugeot W838OBY for £500 to 0xABC..."
          rows={6}
          className="w-full border p-2 rounded"
        />
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
        >
          {loading ? 'Generating…' : 'Generate Contract'}
        </button>
      </form>
    </div>
  )
}

