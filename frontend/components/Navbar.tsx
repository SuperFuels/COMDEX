// frontend/components/Navbar.tsx
import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'
import axios from 'axios'

export default function Navbar() {
  const router = useRouter()
  const [isLoggedIn, setIsLoggedIn]       = useState(false)
  const [role, setRole]                   = useState<string>('')
  const [walletAddress, setWalletAddress] = useState<string | null>(null)

  // 1) Check JWT + fetch role
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token')
      if (!token) {
        setIsLoggedIn(false)
        setRole('')
        return
      }
      try {
        const { data } = await axios.get<{ role: string }>(
          `${process.env.NEXT_PUBLIC_API_URL}/auth/role`,
          { headers: { Authorization: `Bearer ${token}` } }
        )
        setIsLoggedIn(true)
        setRole(data.role)
      } catch {
        setIsLoggedIn(false)
        setRole('')
      }
    }
    checkAuth()
    router.events.on('routeChangeComplete', checkAuth)
    return () => router.events.off('routeChangeComplete', checkAuth)
  }, [router])

  // 2) MetaMask connect
  useEffect(() => {
    if ((window as any).ethereum) {
      ;(window as any).ethereum
        .request({ method: 'eth_requestAccounts' })
        .then((accounts: string[]) => setWalletAddress(accounts[0]))
        .catch(console.error)
    }
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('token')
    setIsLoggedIn(false)
    setRole('')
    router.push('/login')
  }

  const shortAddr = walletAddress
    ? `${walletAddress.slice(0, 6)}…${walletAddress.slice(-4)}`
    : ''

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex-shrink-0">
            <Image
              src="/stickey.png"
              alt="Stickey Logo"
              width={144}
              height={48}
              style={{ width: 'auto', height: 'auto' }}
              priority
            />
          </Link>

          {/* Right: Auth links & wallet */}
          <div className="flex items-center space-x-6">
            {!isLoggedIn ? (
              <>
                <Link href="/login" className="text-sm font-medium text-gray-700 hover:text-gray-900">
                  Login
                </Link>
                <Link href="/register/supplier" className="text-sm font-medium text-gray-700 hover:text-gray-900">
                  Sell
                </Link>
                <Link href="/register/buyer" className="text-sm font-medium text-gray-700 hover:text-gray-900">
                  Buy
                </Link>
              </>
            ) : (
              <>
                {role === 'admin' && (
                  <Link href="/admin/dashboard" className="text-sm font-medium text-gray-700 hover:text-gray-900">
                    Admin
                  </Link>
                )}
                {role === 'supplier' && (
                  <>
                    <Link href="/dashboard" className="text-sm font-medium text-gray-700 hover:text-gray-900">
                      Dashboard
                    </Link>
                    <Link href="/products/create" className="text-sm font-medium text-gray-700 hover:text-gray-900">
                      New Product
                    </Link>
                  </>
                )}
                {role === 'buyer' && (
                  <>
                    <Link href="/" className="text-sm font-medium text-gray-700 hover:text-gray-900">
                      Marketplace
                    </Link>
                    <Link href="/dashboard" className="text-sm font-medium text-gray-700 hover:text-gray-900">
                      Dashboard
                    </Link>
                  </>
                )}
                <button
                  onClick={handleLogout}
                  className="text-sm font-medium text-gray-700 hover:text-gray-900"
                >
                  Logout
                </button>
              </>
            )}

            {walletAddress ? (
              <span className="px-3 py-1 bg-gray-100 rounded-full text-sm font-medium text-gray-800">
                {shortAddr}
              </span>
            ) : (
              <button
                onClick={() => (window as any).ethereum.request({ method: 'eth_requestAccounts' })}
                className="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded"
              >
                Connect Wallet
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

