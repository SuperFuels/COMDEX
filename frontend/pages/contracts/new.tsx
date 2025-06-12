"use client"

import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import api from '@/lib/api'
import SmartQuote from '@/components/SmartQuote'

interface APIProduct {
  id: number
  title: string
  description: string
  price_per_kg: number
}

interface Profile {
  name: string
  business: string
}

export default function NewContractPage() {
  const router = useRouter()
  const { product: productId } = router.query as { product?: string }

  const [product, setProduct] = useState<APIProduct | null>(null)
  const [profile, setProfile] = useState<Profile>({ name: '', business: '' })
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  useEffect(() => {
    if (!productId) return
    setLoading(true)
    setError(null)

    // fetch product
    api
      .get<APIProduct>(`/products/${productId}`)
      .then(({ data }) => setProduct(data))
      .catch(() => setError('Failed to load product'))
      .finally(() => setLoading(false))

    // fetch buyer profile
    api
      .get<Profile>('/auth/profile')
      .then(({ data }) => setProfile(data))
      .catch(() => {})
  }, [productId])

  const handleSign = async () => {
    if (!product) return
    setLoading(true)
    setError(null)

    try {
      const typedData = {
        domain: {
          name: 'COMDEX',
          version: '1',
          chainId: 1,
          verifyingContract: '0xYourContractAddress'
        },
        types: {
          Contract: [
            { name: 'productId', type: 'uint256' },
            { name: 'timestamp', type: 'uint256' },
          ]
        },
        primaryType: 'Contract',
        message: {
          productId: product.id,
          timestamp: Math.floor(Date.now() / 1000),
        },
      }

      const accounts: string[] = await (window as any).ethereum.request({
        method: 'eth_requestAccounts'
      })

      const signature: string = await (window as any).ethereum.request({
        method: 'eth_signTypedData_v4',
        params: [accounts[0], JSON.stringify(typedData)],
      })

      await api.post('/contracts', {
        productId: product.id,
        signature,
      })

      router.push('/buyer/dashboard/deals')
    } catch (err: any) {
      console.error(err)
      setError(err?.response?.data?.detail || 'Failed to submit contract')
    } finally {
      setLoading(false)
    }
  }

  if (loading)      return <p className="p-8 text-center">Loading…</p>
  if (error)        return <p className="p-8 text-center text-red-600">{error}</p>
  if (!product)     return <p className="p-8 text-center">Product not found.</p>

  // price is per-ton, convert from per-kg
  const unitPrice = product.price_per_kg * 1000

  return (
    <main className="mt-[-4rem] pt-0">
      <div className="min-h-screen bg-gray-50">
        <SmartQuote
          buyerName={profile.name}
          buyerBusiness={profile.business}
          walletAddress={''}
          productName={product.title}
          productDesc={product.description}
          quantity={1}
          unitPrice={unitPrice}
          intendedDate={new Date().toISOString().slice(0,10)}
          onSign={handleSign}
        />
      </div>
    </main>
  )
}