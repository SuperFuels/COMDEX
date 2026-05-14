// frontend/components/WalletConnect.tsx
"use client"

import { useState } from 'react'
import api from '../lib/api'

export default function WalletConnect() {
  const [walletAddress, setWalletAddress] = useState<string | null>(null)

  const connectWallet = async () => {
    // avoid TypeScript redeclaration conflicts by casting:
    const eth = (window as any).ethereum as {
      request(args: { method: string; params?: any[] }): Promise<unknown>
    } | undefined

    if (!eth) {
      alert('🦊 MetaMask not detected')
      return
    }

    try {
      const accounts = (await eth.request({
        method: 'eth_requestAccounts',
      })) as string[] | null

      if (!accounts || accounts.length === 0) {
        throw new Error('No accounts returned')
      }

      const address = accounts[0]
      setWalletAddress(address)

      const token = localStorage.getItem('token')
      if (!token) {
        alert('🔐 Please log in first to bind your wallet')
        return
      }

      await api.patch(
        '/users/me/wallet',
        { wallet_address: address },
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      )

      console.log('✅ Wallet successfully linked to user account')
    } catch (err) {
      console.error('Wallet Connect Error:', err)
      alert('🛑 Wallet connection failed')
    }
  }

  return (
    <div className="text-center mt-4">
      {walletAddress ? (
        <p className="text-green-600 font-mono">🔗 {walletAddress}</p>
      ) : (
        <button
          onClick={connectWallet}
          className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
        >
          Connect Wallet
        </button>
      )}
    </div>
  )
}
