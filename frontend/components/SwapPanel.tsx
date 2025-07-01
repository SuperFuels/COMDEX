// frontend/components/SwapPanel.tsx
"use client"

import React, { useState, useEffect } from 'react'
import { ethers } from 'ethers'
import Image from 'next/image'
import gluAbi from '../abi/GLU.json'
import escrowAbi from '../abi/GLUEscrow.json'

interface SwapPanelProps {
  supplierAddress: string
  pricePerKg: number      // USD per kg
  onSuccess: () => void
}

export default function SwapPanel({
  supplierAddress,
  pricePerKg,
  onSuccess,
}: SwapPanelProps) {
  const [qty, setQty] = useState<number>(0)
  const [tokenContract, setTokenContract] = useState<ethers.Contract | null>(null)
  const [escrowContract, setEscrowContract] = useState<ethers.Contract | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const tokenAddress  = process.env.NEXT_PUBLIC_GLU_TOKEN_ADDRESS!
  const escrowAddress = process.env.NEXT_PUBLIC_ESCROW_ADDRESS!

  // Connect wallet & instantiate contracts
  useEffect(() => {
    if (typeof window === 'undefined' || !(window as any).ethereum) {
      setError('Please install MetaMask.')
      return
    }
    const provider = new ethers.providers.Web3Provider(
      (window as any).ethereum,
      { name: 'localhost', chainId: 31337 }
    )
    provider.send('eth_requestAccounts', [])
      .then(() => {
        const signer = provider.getSigner()
        setTokenContract(
          new ethers.Contract(tokenAddress, (gluAbi as any).abi, signer)
        )
        setEscrowContract(
          new ethers.Contract(escrowAddress, (escrowAbi as any).abi, signer)
        )
      })
      .catch(() => setError('Wallet connection failed'))
  }, [tokenAddress, escrowAddress])

  const handleDeposit = async () => {
    setError(null)
    if (qty <= 0) {
      setError('Enter a positive quantity')
      return
    }
    if (!tokenContract || !escrowContract) {
      setError('Wallet not connected')
      return
    }

    setLoading(true)
    try {
      // 1 GLU ≈ 1 USD
      const amountGlu = ethers.utils.parseUnits(
        (qty * pricePerKg).toString(),
        18
      )

      // a) Approve escrow
      const approveTx = await tokenContract.approve(escrowAddress, amountGlu)
      await approveTx.wait()

      // b) Create escrow on‐chain
      const tx = await escrowContract.createEscrow(
        supplierAddress,
        amountGlu
      )
      await tx.wait()

      onSuccess()
    } catch (err: any) {
      setError(err.message ?? 'Transaction failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-4 border rounded bg-gray-50 flex flex-col space-y-4">
      {/* Quantity */}
      <label className="block">
        <span className="mb-1 font-medium block">Quantity (kg):</span>
        <input
          type="number"
          value={qty || ''}
          onChange={e => setQty(parseFloat(e.target.value))}
          className="w-24 p-2 border rounded focus:outline-none focus:ring-2 focus:ring-primary"
          min="0"
          step="0.01"
        />
      </label>

      {/* Total GLU */}
      <p className="flex items-center text-lg">
        <span className="mr-2">Total GLU:</span>
        <strong className="inline-flex items-center">
          {(qty * pricePerKg).toFixed(2)}
          <Image
            src="/glu.svg"
            alt="GLU token"
            width={20}
            height={20}
            className="ml-1"
            priority
          />
        </strong>
      </p>

      {/* Error */}
      {error && <p className="text-red-600">{error}</p>}

      {/* Deposit Button */}
      <button
        onClick={handleDeposit}
        disabled={loading}
        className="inline-flex items-center justify-center px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
      >
        <Image
          src="/glu.svg"
          alt="GLU"
          width={16}
          height={16}
          className="mr-2"
          priority
        />
        {loading ? 'Processing…' : 'Lock GLU in Escrow'}
      </button>
    </div>
  )
}

