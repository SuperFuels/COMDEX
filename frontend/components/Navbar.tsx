// frontend/components/Navbar.tsx

import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/router'
import { useEffect, useState, useRef, useCallback } from 'react'
import api from '@/lib/api'
import { UserRole } from '@/hooks/useAuthRedirect'

export default function Navbar() {
  const router = useRouter()

  // ─── track connected account & current role ────────────────
  const [account, setAccount] = useState<string | null>(null)
  const [role, setRole] = useState<UserRole | null>(null)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)

  // ─── SIWE login helper ───────────────────────────
  const doLogin = useCallback(
    async (address: string) => {
      try {
        const {
          data: { nonce, message },
        } = await api.get('/auth/nonce', { params: { address } })

        // sign with MetaMask
        const signature: string = await (window as any).ethereum.request({
          method: 'personal_sign',
          params: [message, address],
        })

        // verify on server
        const {
          data: { token, role: newRole },
        } = await api.post('/auth/verify', { message, signature })

        // success → store token + role
        localStorage.setItem('token', token)
        api.defaults.headers.common.Authorization = `Bearer ${token}`
        setRole(newRole as UserRole)
      } catch (err: any) {
        // if we get a 404, go register
        if (err.response?.status === 404) {
          router.push('/register')
          return
        }

        // otherwise, treat as normal login failure
        console.error('SIWE login failed:', err.response?.data ?? err.message)
        localStorage.removeItem('token')
        delete api.defaults.headers.common.Authorization
        setRole(null)
      }
    },
    [router]
  )

  // ─── Handle account changes ───────────────────────
  const handleAccountsChanged = useCallback(
    (accounts: string[]) => {
      const addr = accounts[0] || null
      if (addr && addr !== account) {
        // new wallet => reset and re-login
        localStorage.removeItem('token')
        delete api.defaults.headers.common.Authorization
        setAccount(addr)
        setRole(null)
        doLogin(addr)
      } else if (!addr) {
        // disconnected
        handleDisconnect()
      }
    },
    [account, doLogin]
  )

  // ─── On mount: hydrate token & subscribe to wallet changes ─────
  useEffect(() => {
    const eth = (window as any).ethereum
    if (!eth) return

    // hydrate existing token
    const token = localStorage.getItem('token')
    if (token) {
      api.defaults.headers.common.Authorization = `Bearer ${token}`
      api
        .get('/auth/role')
        .then(res => setRole(res.data.role as UserRole))
        .catch(() => {
          localStorage.removeItem('token')
          delete api.defaults.headers.common.Authorization
          setRole(null)
        })
    }

    // check currently connected account
    eth
      .request({ method: 'eth_accounts' })
      .then((accounts: string[]) => {
        const addr = accounts[0] || null
        setAccount(addr)
        if (addr && !token) doLogin(addr)
      })
      .catch(console.error)

    eth.on('accountsChanged', handleAccountsChanged)
    return () => {
      eth.removeListener('accountsChanged', handleAccountsChanged)
    }
  }, [doLogin, handleAccountsChanged])

  // ─── Disconnect handler ─────────────────────────
  const handleDisconnect = () => {
    localStorage.removeItem('token')
    delete api.defaults.headers.common.Authorization
    setAccount(null)
    setRole(null)
    setDropdownOpen(false)
    router.push('/')
  }

  // ─── Connect wallet button ───────────────────────
  const handleConnect = async () => {
    const eth = (window as any).ethereum
    if (!eth) return alert('Please install MetaMask')
    try {
      const accounts: string[] = await eth.request({
        method: 'eth_requestAccounts',
      })
      const addr = accounts[0]
      setAccount(addr)
      doLogin(addr)
    } catch (err) {
      console.error(err)
    }
  }

  // ─── Close dropdown when clicking outside ─────────
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (
        dropdownOpen &&
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [dropdownOpen])

  const shortAddr = account
    ? `${account.slice(0, 6)}…${account.slice(-4)}`
    : ''

  return (
    <header className="sticky top-0 bg-white border-b z-50">
      <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4">
        {/* Logo */}
        <Link href="/" passHref>
          <a>
            <Image
              src="/stickey.png"
              width={144}
              height={48}
              alt="Logo"
              priority
            />
          </a>
        </Link>

        {/* Navigation */}
        <div className="flex items-center space-x-6">
          {/* always visible */}
          <Link href="/" passHref>
            <a className="text-gray-700 hover:underline">Marketplace</a>
          </Link>

          {/* show Register until you’ve connected & registered */}
          {!account && (
            <Link href="/register" passHref>
              <a className="text-gray-700 hover:underline">Register</a>
            </Link>
          )}

          {/* role-based dashboard links */}
          {role === 'supplier' && (
            <Link href="/dashboard" passHref>
              <a className="text-gray-700 hover:underline">
                Supplier Dashboard
              </a>
            </Link>
          )}
          {role === 'buyer' && (
            <Link href="/buyer/dashboard" passHref>
              <a className="text-gray-700 hover:underline">
                Buyer Dashboard
              </a>
            </Link>
          )}
          {role === 'admin' && (
            <Link href="/admin/dashboard" passHref>
              <a className="text-gray-700 hover:underline">Admin Dashboard</a>
            </Link>
          )}

          {/* connect button vs connected state */}
          {!account ? (
            <button
              onClick={handleConnect}
              className="bg-blue-600 text-white px-3 py-1 rounded"
            >
              Connect Wallet
            </button>
          ) : (
            <div ref={wrapperRef} className="relative">
              <button
                onClick={() => setDropdownOpen(o => !o)}
                className="bg-gray-100 px-3 py-1 rounded-full border border-gray-300"
              >
                {shortAddr}
              </button>
              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-40 bg-white border rounded shadow-md">
                  <button
                    onClick={handleDisconnect}
                    className="w-full text-left px-4 py-2 hover:bg-gray-100"
                  >
                    Disconnect
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

