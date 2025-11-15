// File: frontend/pages/register.tsx
"use client"

import { useState, FormEvent } from 'react'
import { useRouter } from 'next/router'
import Link from 'next/link'
import Select from 'react-select'
// ❌ remove ethers import
// import { ethers } from 'ethers'
import api from '@/lib/api'
import { slugFromEmail, ensureContainersForWA } from '@/lib/containers'  // ⬅️ NEW

type Role = 'buyer' | 'supplier' | 'admin'   // ⬅️ fix typo

interface ProductOption {
  value: string
  label: string
}

const PRODUCT_OPTIONS: ProductOption[] = [
  { value: 'olive_oil', label: 'Olive Oil' },
  { value: 'butter', label: 'Butter' },
  { value: 'whey_protein', label: 'Whey Protein' },
]

export default function RegisterPage() {
  const router = useRouter()
  const [step, setStep] = useState<1 | 2>(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [role, setRole] = useState<Role>('buyer')

  // 🔇 wallet is dormant for now
  const [walletAddress] = useState<string | null>(null)

  const handleConnectWallet = () => {
    // Dormant stub: present but disabled. Keep UI parity without MetaMask.
    alert('Wallet connection will be available when our chain is live.')
  }

  const handleStep1 = (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!fullName || !email || !password || !confirm || password !== confirm) {
      setError('Please fill all fields & ensure passwords match.')
      return
    }
    // ⛔ remove requirement for wallet
    setStep(2)
  }

  const [businessName, setBusinessName] = useState('')
  const [address, setAddress] = useState('')
  const [deliveryAddress, setDeliveryAddress] = useState('')
  const [products, setProducts] = useState<ProductOption[]>([])
  const [monthlySpend, setMonthlySpend] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const payload: any = {
        name: fullName,
        email,
        password,
        role,
        // keep field for compatibility but null/empty
        wallet_address: null,
      }

      if (role === 'supplier') {
        payload.business_name = businessName
        payload.address = address
        payload.delivery_address = deliveryAddress
        payload.products = products.map((p) => p.value)
      } else if (role === 'buyer') {
        payload.monthly_spend = monthlySpend
      }

      await api.post('/auth/register', payload)

      // ⬇️ NEW: align containers at registration time
      const userSlug = slugFromEmail(email)
      const wa = `${userSlug}@wave.tp`
      localStorage.setItem('gnet:user_slug', userSlug)
      localStorage.setItem('gnet:wa', wa)
      ensureContainersForWA(wa)

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
        <h1 className="text-2xl font-bold text-center mb-6">New User Activation</h1>

        {error && <p className="text-red-600 text-center mb-4">{error}</p>}

        <form onSubmit={step === 1 ? handleStep1 : handleSubmit} className="space-y-6">
          {step === 1 ? (
            <>
              {/* ...Full Name / Email / Password fields unchanged... */}

              <div>
                <label className="block font-medium mb-1">I am a</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as Role)}
                  className="w-full border rounded px-3 py-2 focus:outline-none focus:ring"
                >
                  <option value="buyer">Buyer</option>
                  <option value="supplier">Supplier</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              {/* Dormant wallet button */}
              <div>
                <button
                  type="button"
                  onClick={handleConnectWallet}
                  disabled
                  className="w-full py-2 rounded text-white bg-gray-400 cursor-not-allowed"
                  title="Coming soon"
                >
                  Connect Wallet (coming soon)
                </button>
              </div>

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
              {/* supplier / buyer fields unchanged */}
              {/* ... */}
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