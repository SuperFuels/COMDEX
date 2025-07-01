// File: frontend/pages/register.tsx
"use client"

import { useState, FormEvent } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import Select, { OnChangeValue, MultiValue } from 'react-select'
import { ethers } from 'ethers'
import api from '@/lib/api' // assumes api is preconfigured with NEXT_PUBLIC_API_URL

type Role = 'buyer' | 'supplier'

interface ProductOption {
  value: string
  label: string
}

const PRODUCT_OPTIONS: ProductOption[] = [
  { value: 'olive_oil',    label: 'Olive Oil'    },
  { value: 'butter',       label: 'Butter'       },
  { value: 'whey_protein', label: 'Whey Protein' },
  // …add more here
]

export default function RegisterPage() {
  const router = useRouter()

  // ─── Step control ──────────────────────────────────────────────
  const [step, setStep]       = useState<1 | 2>(1)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)

  // ─── Step 1 fields ─────────────────────────────────────────────
  const [fullName, setFullName]           = useState('')
  const [email, setEmail]                 = useState('')
  const [password, setPassword]           = useState('')
  const [confirm, setConfirm]             = useState('')
  const [role, setRole]                   = useState<Role>('buyer')
  const [walletAddress, setWalletAddress] = useState<string | null>(null)

  // ─── Step 2 fields ─────────────────────────────────────────────
  const [businessName, setBusinessName]       = useState('')
  const [address, setAddress]                 = useState('')
  const [deliveryAddress, setDeliveryAddress] = useState('')
  const [products, setProducts]               = useState<ProductOption[]>([])
  const [monthlySpend, setMonthlySpend]       = useState('')

  // 1) Connect wallet (pure client-side)
  const handleConnectWallet = async () => {
    try {
      if (!(window as any).ethereum) {
        throw new Error('No Ethereum provider found')
      }
      const provider = new ethers.providers.Web3Provider(
        (window as any).ethereum,
        'any'
      )
      await provider.send('eth_requestAccounts', [])
      const signer = provider.getSigner()
      const addr = await signer.getAddress()
      setWalletAddress(addr)
    } catch (err) {
      console.error(err)
      alert('Wallet connection failed')
    }
  }

  // 2) Validate step 1 & advance
  const handleStep1 = (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    if (
      !fullName ||
      !email ||
      !password ||
      !confirm ||
      password !== confirm
    ) {
      setError('Please fill all fields & ensure passwords match.')
      return
    }
    if (!walletAddress) {
      setError('Please connect your wallet.')
      return
    }
    setStep(2)
  }

  // 3) Final submission
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const payload: any = {
        name:             fullName,
        email,
        password,
        role,
        wallet_address:   walletAddress,
        business_name:    businessName,
        address,
        delivery_address: deliveryAddress,
        products:         products.map((p) => p.value),
      }
      if (role === 'buyer') {
        payload.monthly_spend = monthlySpend
      }
      // Note: do NOT prefix with "/api" — FastAPI now listens on "/auth"
      await api.post('/auth/register', payload)
      router.push('/login')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed')
      setLoading(false)
      return
    }

    setLoading(false)
  }

  return (
    <main className="pt-0 min-h-screen bg-gray-100 flex items-center justify-center px-4">
      <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-2xl">
        <h1 className="text-2xl font-bold text-center mb-6">
          New User Activation
        </h1>

        {error && <p className="text-red-600 text-center mb-4">{error}</p>}

        <form
          onSubmit={step === 1 ? handleStep1 : handleSubmit}
          className="space-y-6"
        >
          {step === 1 ? (
            <>
              {/* Full Name */}
              <div>
                <label className="block font-medium mb-1">Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  className="w-full border rounded px-3 py-2 focus:outline-none focus:ring"
                />
              </div>

              {/* Email */}
              <div>
                <label className="block font-medium mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full border rounded px-3 py-2 focus:outline-none focus:ring"
                />
              </div>

              {/* Password */}
              <div>
                <label className="block font-medium mb-1">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full border rounded px-3 py-2 focus:outline-none focus:ring"
                />
              </div>

              {/* Confirm Password */}
              <div>
                <label className="block font-medium mb-1">
                  Confirm Password
                </label>
                <input
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  required
                  className="w-full border rounded px-3 py-2 focus:outline-none focus:ring"
                />
              </div>

              {/* Role Selector */}
              <div>
                <label className="block font-medium mb-1">I am a</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as Role)}
                  className="w-full border rounded px-3 py-2 focus:outline-none focus:ring"
                >
                  <option value="buyer">Buyer</option>
                  <option value="supplier">Supplier</option>
                </select>
              </div>

              {/* Wallet Connect */}
              <div>
                <button
                  type="button"
                  onClick={handleConnectWallet}
                  className={`w-full py-2 rounded text-white ${
                    walletAddress ? 'bg-green-600' : 'bg-blue-600'
                  }`}
                >
                  {walletAddress
                    ? `Connected: ${walletAddress.slice(0, 6)}…${walletAddress.slice(-4)}`
                    : 'Connect Wallet'}
                </button>
              </div>

              {/* Next Step */}
              <div className="flex justify-end">
                <button
                  type="submit"
                  className="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                >
                  Next →
                </button>
              </div>
            </>
          ) : (
            <>
              {/* Business Name */}
              <div>
                <label className="block font-medium mb-1">
                  Business Name
                </label>
                <input
                  type="text"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  className="w-full border rounded px-3 py-2 focus:outline-none focus:ring"
                />
              </div>

              {/* Address */}
              <div>
                <label className="block font-medium mb-1">Address</label>
                <input
                  type="text"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  className="w-full border rounded px-3 py-2 focus:outline-none focus:ring"
                />
              </div>

              {/* Delivery Address */}
              <div>
                <label className="block font-medium mb-1">
                  Delivery Address (if different)
                </label>
                <input
                  type="text"
                  value={deliveryAddress}
                  onChange={(e) => setDeliveryAddress(e.target.value)}
                  className="w-full border rounded px-3 py-2 focus:outline-none focus:ring"
                />
              </div>

              {/* Products Selector */}
              <div>
                <label className="block font-medium mb-1">
                  Products you {role === 'buyer' ? 'purchase' : 'sell'}
                </label>
                <Select<ProductOption, true>
                  isMulti
                  options={PRODUCT_OPTIONS}
                  value={products}
                  onChange={(opts: OnChangeValue<ProductOption, true>) => {
                    setProducts([...(opts as readonly ProductOption[])])
                  }}
                  placeholder="Select product categories…"
                />
              </div>

              {/* Monthly Spend for Buyers */}
              {role === 'buyer' && (
                <div>
                  <label className="block font-medium mb-1">
                    Current monthly spend on commodities
                  </label>
                  <input
                    type="text"
                    value={monthlySpend}
                    onChange={(e) => setMonthlySpend(e.target.value)}
                    className="w-full border rounded px-3 py-2 focus:outline-none focus:ring"
                  />
                </div>
              )}

              {/* Back & Activate Buttons */}
              <div className="flex justify-between items-center">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="px-4 py-2 bg-gray-400 text-white rounded hover:bg-gray-500"
                >
                  ← Back
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                >
                  {loading ? 'Activating…' : 'Activate'}
                </button>
              </div>
            </>
          )}
        </form>

        <p className="mt-6 text-center text-sm text-gray-600">
          Already have an account?{' '}
          <Link href="/login" className="text-blue-600 hover:underline">
            Login
          </Link>
        </p>
      </div>
    </main>
  )
}