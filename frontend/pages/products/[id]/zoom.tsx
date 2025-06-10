// frontend/pages/products/[id]/zoom.tsx
"use client"

import { useRouter } from 'next/router'
import { useState } from 'react'
import Link from 'next/link'

export default function ZoomRequestPage() {
  const router = useRouter()
  const { id } = router.query
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [datetime, setDatetime] = useState('')
  const [notes, setNotes] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: POST to your API endpoint, e.g.:
    // await api.post('/api/zoom-requests', { productId: id, name, email, datetime, notes })
    setSubmitted(true)
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-md mx-auto bg-white p-6 rounded shadow">
        <h1 className="text-xl font-bold mb-4">Request a Zoom Call</h1>

        {!submitted ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium">Your Name</label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                required
                className="mt-1 w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium">Your Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                className="mt-1 w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium">Preferred Date & Time</label>
              <input
                type="datetime-local"
                value={datetime}
                onChange={e => setDatetime(e.target.value)}
                required
                className="mt-1 w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium">Additional Notes</label>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                className="mt-1 w-full p-2 border rounded"
              />
            </div>
            <button
              type="submit"
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded"
            >
              Send Zoom Request
            </button>
          </form>
        ) : (
          <div className="text-center space-y-4">
            <p className="text-lg">✅ Your request has been sent!</p>
            <p className="text-sm text-gray-600">
              The supplier will reach out to confirm and share the meeting link.
            </p>
            <Link legacyBehavior href={`/products/${id}`} className="text-blue-600 hover:underline">
              ← Back to product
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}

