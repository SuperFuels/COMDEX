// frontend/components/Navbar.tsx
"use client"

import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/router'
import { useEffect, useState } from 'react'

export default function Navbar() {
  const router = useRouter()
  const [account, setAccount] = useState<string | null>(null)

  useEffect(() => {
    const { ethereum } = window as any
    if (!ethereum) return

    // On load: get any connected account
    ethereum
      .request({ method: 'eth_accounts' })
      .then((accounts: string[]) => {
        if (accounts[0]) {
          setAccount(accounts[0])
        }
      })
      .catch(console.error)

    // Listen for account changes
    const handleAccountsChanged = (accounts: string[]) => {
      setAccount(accounts[0] || null)
    }
    ethereum.on('accountsChanged', handleAccountsChanged)
    return () => {
      ethereum.removeListener('accountsChanged', handleAccountsChanged)
    }
  }, [])

  const handleConnect = async () => {
    const { ethereum } = window as any
    if (!ethereum) {
      alert('Please install MetaMask')
      return
    }
    try {
      const accounts: string[] = await ethereum.request({ method: 'eth_requestAccounts' })
      setAccount(accounts[0])
    } catch (err) {
      console.error('Wallet connect failed', err)
    }
  }

  const handleDisconnect = () => {
    setAccount(null)
    router.push('/')   // send them home
  }

  const shortAddr = account
    ? `${account.slice(0, 6)}…${account.slice(-4)}`
    : ''

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link legacyBehavior href="/">
          <Image src="/stickey.png" alt="Stickey Logo" width={144} height={48} priority />
        </Link>

        {/* Navigation & Wallet */}
        <div className="flex items-center space-x-6">
          <Link legacyBehavior href="/" className="text-sm font-medium text-gray-700 hover:underline">
            Marketplace
          </Link>

          {!account ? (
            <button
              onClick={handleConnect}
              className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded"
            >
              Connect Wallet
            </button>
          ) : (
            <div className="relative inline-block group">
              {/* Address Button */}
              <button className="px-3 py-1 bg-gray-100 rounded-full text-sm font-medium border border-gray-300">
                {shortAddr}
              </button>

              {/* Dropdown: stays visible on hover */}
              <div className="absolute right-0 mt-2 hidden group-hover:block hover:block bg-white border border-gray-200 rounded shadow-lg z-50">
                <button
                  onClick={handleDisconnect}
                  className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                >
                  Disconnect
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

