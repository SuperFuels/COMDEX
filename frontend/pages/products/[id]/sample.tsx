import { useRouter } from 'next/router'
import { useState } from 'react'
import Link from 'next/link'

export default function SampleRequestPage() {
  const router = useRouter()
  const { id } = router.query
  const [name, setName] = useState('')
  const [address, setAddress] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: POST to your API: /samples with { product: id, name, address }
    setSubmitted(true)
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-md mx-auto bg-white p-6 rounded shadow">
        <h1 className="text-xl font-bold mb-4">Order Sample</h1>
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
              <label className="block text-sm font-medium">Business Address</label>
              <textarea
                value={address}
                onChange={e => setAddress(e.target.value)}
                required
                className="mt-1 w-full p-2 border rounded"
              />
            </div>
            <button
              type="submit"
              className="w-full py-2 bg-blue-600 text-white font-medium rounded"
            >
              Send Sample Request
            </button>
          </form>
        ) : (
          <div className="text-center space-y-4">
            <p className="text-lg">✅ Your sample request has been sent!</p>
            <p className="text-sm text-gray-600">
              The supplier will confirm cost & delivery, then send you a quote under
              Notifications.
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

