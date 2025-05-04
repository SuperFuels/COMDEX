// frontend/components/SwapPanel.tsx

import React, { useState } from 'react'
import axios from 'axios'

interface SwapPanelProps {
  productId: number
  pricePerKg: number
  onSuccess: () => void
}

export default function SwapPanel({
  productId,
  pricePerKg,
  onSuccess,
}: SwapPanelProps) {
  const [qty, setQty] = useState<number>(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    setError(null)
    if (qty <= 0) {
      setError('Please enter a quantity greater than zero.')
      return
    }

    const token = localStorage.getItem('token')
    if (!token) {
      setError('You must be logged in to create a deal.')
      return
    }

    setLoading(true)
    try {
      await axios.post(
        'http://localhost:8000/deals/',
        { product_id: productId, quantity_kg: qty },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )
      onSuccess()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create deal.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-4 border rounded bg-gray-50">
      <label className="block mb-2">
        Quantity (kg):
        <input
          type="number"
          value={qty || ''}
          onChange={(e) => setQty(parseFloat(e.target.value))}
          className="ml-2 p-1 border rounded w-20"
          min="0"
          step="0.01"
        />
      </label>

      <p className="mb-4">
        Total: <strong>${(qty * pricePerKg).toFixed(2)}</strong>
      </p>

      {error && <p className="text-red-600 mb-2">{error}</p>}

      <button
        onClick={handleSubmit}
        disabled={loading}
        className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
      >
        {loading ? 'Creating…' : 'Confirm Quote'}
      </button>
    </div>
  )
}

