// frontend/pages/contracts/new.tsx

import { useState } from 'react'
import { useRouter } from 'next/router'
import axios from 'axios'

export default function NewContractPage() {
  const router = useRouter()
  const [prompt, setPrompt]   = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string|null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim()) {
      setError('Please enter a prompt.')
      return
    }
    setLoading(true)
    setError(null)

    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('Not authenticated')

      const { data } = await axios.post(
        'http://localhost:8000/contracts/generate',
        { prompt: prompt.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      )

      // redirect to your new contract’s detail page
      router.push(`/contracts/${data.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message)
      setLoading(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Generate Contract</h1>
      {error && <p className="text-red-600 mb-2">{error}</p>}
      <form onSubmit={handleSubmit}>
        <label className="block mb-2">
          Contract Prompt
          <textarea
            className="w-full p-2 border rounded mt-1 h-32"
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 bg-blue-600 text-white rounded disabled:opacity-50"
        >
          {loading ? 'Generating…' : 'Generate Contract'}
        </button>
      </form>
    </div>
  )
}

