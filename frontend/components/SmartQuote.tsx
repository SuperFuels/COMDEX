// frontend/components/SmartQuote.tsx
import React from 'react'
import { format } from 'date-fns'

interface SmartQuoteProps {
  buyerName: string
  buyerBusiness: string
  walletAddress: string
  productName: string
  productDesc: string
  quantity: number
  unitPrice?: number           // made optional to avoid undefined
  intendedDate: string
  onSign: () => Promise<void>
}

export default function SmartQuote({
  buyerName,
  buyerBusiness,
  walletAddress,
  productName,
  productDesc,
  quantity,
  unitPrice = 0,               // default to 0 if not provided
  intendedDate,
  onSign,
}: SmartQuoteProps) {
  const safeUnitPrice = unitPrice
  const total = quantity * safeUnitPrice
  const today = format(new Date(), 'MMMM d, yyyy')
  const intended = format(new Date(intendedDate), 'MMMM d, yyyy')

  return (
    <div className="max-w-3xl mx-auto bg-white shadow-xl p-8 rounded-lg">
      {/* Header */}
      <header className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">Smart Quote</h1>
          <p className="text-sm text-gray-500">{today}</p>
        </div>
        <div className="text-right">
          <p className="font-medium">{buyerBusiness}</p>
          <p className="text-sm">{buyerName}</p>
          <p className="text-sm truncate">{walletAddress}</p>
        </div>
      </header>

      {/* Quote Details */}
      <table className="w-full mb-6 border-collapse">
        <thead>
          <tr className="bg-gray-100">
            <th className="px-4 py-2 text-left">Product</th>
            <th className="px-4 py-2 text-left">Description</th>
            <th className="px-4 py-2 text-center">Qty</th>
            <th className="px-4 py-2 text-center">Unit Price</th>
            <th className="px-4 py-2 text-center">Total</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="px-4 py-2">{productName}</td>
            <td className="px-4 py-2">{productDesc}</td>
            <td className="px-4 py-2 text-center">{quantity}</td>
            <td className="px-4 py-2 text-center">£{safeUnitPrice.toFixed(2)}</td>
            <td className="px-4 py-2 text-center">£{total.toFixed(2)}</td>
          </tr>
        </tbody>
      </table>

      {/* Metadata */}
      <div className="mb-8">
        <p>
          <span className="font-semibold">Intended Purchase Date:</span>{' '}
          {intended}
        </p>
      </div>

      {/* Signature Section */}
      <div className="flex flex-col sm:flex-row justify-between items-center space-y-4 sm:space-y-0">
        <button
          onClick={onSign}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          Sign &amp; Submit
        </button>
        <p className="text-xs text-gray-500 text-center sm:text-right">
          By signing, you agree to our standard terms.
        </p>
      </div>
    </div>
  )
}
