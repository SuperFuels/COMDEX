// frontend/components/QuoteModal.tsx

import { useState } from 'react'
import axios from 'axios'
import { useRouter } from 'next/router'
import styles from './QuoteModal.module.css'

interface QuoteModalProps {
  productId:     number
  productTitle:  string
  supplierEmail: string
  pricePerKg:    number
  onClose:       () => void
}

export default function QuoteModal({
  productId,
  productTitle,
  supplierEmail,
  pricePerKg,
  onClose,
}: QuoteModalProps) {
  const router = useRouter()
  const [quantity, setQuantity] = useState<number>(1)
  const [loading,  setLoading]   = useState<boolean>(false)
  const [error,    setError]     = useState<string | null>(null)

  const handleConfirm = async (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault()        // ← stop any native navigation
    setError(null)

    if (quantity <= 0) {
      setError('Please enter a quantity greater than 0')
      return
    }

    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('Not authenticated')

      // Decode buyer email from the JWT sub claim
      const payload    = JSON.parse(atob(token.split('.')[1]))
      const buyerEmail = payload.sub as string

      const totalPrice = quantity * pricePerKg
      const body = {
        buyer_email:    buyerEmail,
        supplier_email: supplierEmail,
        product_title:  productTitle,
        quantity_kg:    quantity,
        total_price:    totalPrice,
      }

      const res = await axios.post(
        'http://localhost:8000/deals/',
        body,
        { headers: { Authorization: `Bearer ${token}` } }
      )

      const deal = res.data
      onClose()                             // close the modal
      router.push(`/deals/${deal.id}`)      // navigate to the new deal’s page
    } catch (err: any) {
      console.error(err)
      const detail = err.response?.data?.detail
      if (Array.isArray(detail)) {
        setError(detail.map((d: any) => d.msg).join('; '))
      } else if (typeof detail === 'string') {
        setError(detail)
      } else {
        setError('Failed to create quote.')
      }
      setLoading(false)
    }
  }

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modalContent}>
        <button
          className={styles.closeButton}
          onClick={onClose}
          aria-label="Close"
        >
          ×
        </button>

        <h2 className="text-xl font-bold mb-4">Generate Quote</h2>
        {error && <p className="text-red-600 mb-2">{error}</p>}

        <label htmlFor="quantity" className="block mb-2">
          Quantity (kg)
          <input
            id="quantity"
            name="quantity"
            type="number"
            min={1}
            value={quantity}
            onChange={e => setQuantity(Number(e.target.value))}
            className="w-full p-2 border rounded mt-1"
          />
        </label>

        <button
          onClick={handleConfirm}
          disabled={loading}
          className="w-full py-2 bg-blue-600 text-white rounded mt-4 disabled:opacity-50"
        >
          {loading ? 'Submitting…' : 'Confirm Quote'}
        </button>
      </div>
    </div>
  )
}

