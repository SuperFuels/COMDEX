// components/Navbar.tsx

import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/router'
import { useEffect, useState, useRef, useCallback } from 'react'
import api from '@/lib/api'
import { UserRole } from '@/hooks/useAuthRedirect'

export default function Navbar() {
  const router = useRouter()
  const [account, setAccount] = useState<string | null>(null)
  const [role, setRole] = useState<UserRole | null>(null)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)

  // ─── SIWE login helper ───────────────────────
  const doLogin = useCallback(
    async (address: string) => {
      try {
        // 1) fetch nonce + message
        const {
          data: { nonce, message },
        } = await api.get('/auth/nonce', { params: { address } })

        // 2) sign with MetaMask
        const signature: string = await (window as any).ethereum.request({
          method: 'personal_sign',
          params: [message, address],
        })

        // 3) verify on server
        const {
          data: { token, role: newRole },
        } = await api.post('/auth/verify', { message, signature })

        // 4) persist & set up for future requests
        localStorage.setItem('token', token)
        api.defaults.headers.common.Authorization = `Bearer ${token}`
        setRole(newRole as UserRole)
      } catch (err: any) {
        console.error(
          'SIWE login failed:',
          err.response?.data ?? err.message
        )
        // clear any bad token
        localStorage.removeItem('token')
        delete api.defaults.headers.common.Authorization
        setRole(null)
      }
    },
    []
  )

  // ─── Handle account changes (switch / disconnect) ──────────────────
  const handleAccountsChanged = useCallback(
    (accounts: string[]) => {
      const addr = accounts[0] || null
      if (addr && addr !== account) {
        // new wallet: clear old auth and re-login
        localStorage.removeItem('token')
        delete api.defaults.headers.common.Authorization
        setAccount(addr)
        setRole(null)
        doLogin(addr)
      } else if (!addr) {
        // completely disconnected
        handleDisconnect()
      }
    },
    [account, doLogin]
  )

  // ─── On-mount: hydrate & subscribe ─────────────────────────────────
  useEffect(() => {
    const eth = (window as any).ethereum
    if (!eth) return

    // a) hydrate token if any
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

    // b) check current account
    eth
      .request({ method: 'eth_accounts' })
      .then((accounts: string[]) => {
        const addr = accounts[0] || null
        setAccount(addr)
        if (addr && !token) {
          doLogin(addr)
        }
      })
      .catch(console.error)

    // c) listen for changes
    eth.on('accountsChanged', handleAccountsChanged)
    return () => {
      eth.removeListener('accountsChanged', handleAccountsChanged)
    }
  }, [doLogin, handleAccountsChanged])

  // ─── Disconnect handler ─────────────────────────────────────────────
  const handleDisconnect = () => {
    localStorage.removeItem('token')
    delete api.defaults.headers.common.Authorization
    setAccount(null)
    setRole(null)
    setDropdownOpen(false)
    router.push('/')
  }

  // ─── Connect wallet button ──────────────────────────────────────────
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

  // ─── Close dropdown when clicking outside ──────────────────────────
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
          <Image
            src="/stickey.png"
            width={144}
            height={48}
            alt="Logo"
            priority
          />
        </Link>

        {/* Navigation */}
        <div className="flex items-center space-x-6">
          <Link href="/" className="text-gray-700 hover:underline">
            Marketplace
          </Link>

          {role === 'supplier' && (
            <Link
              href="/dashboard"
              prefetch={false}
              className="text-gray-700 hover:underline"
            >
              Supplier Dashboard
            </Link>
          )}
          {role === 'buyer' && (
            <Link
              href="/buyer/dashboard"
              prefetch={false}
              className="text-gray-700 hover:underline"
            >
              Buyer Dashboard
            </Link>
          )}
          {role === 'admin' && (
            <Link
              href="/admin/dashboard"
              prefetch={false}
              className="text-gray-700 hover:underline"
            >
              Admin Dashboard
            </Link>
          )}

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
                <div className="absolute right-0 mt-2 w-40 bg-white border rounded shadow">
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

