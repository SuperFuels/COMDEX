// frontend/components/SwapPanel.tsx

console.log(
  "TOKEN  →", process.env.NEXT_PUBLIC_GLU_TOKEN_ADDRESS,
  "ESCROW →", process.env.NEXT_PUBLIC_ESCROW_ADDRESS
);

import React, { useState, useEffect } from 'react'
import { ethers } from 'ethers'
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

  // from .env.local
  const tokenAddress  = process.env.NEXT_PUBLIC_GLU_TOKEN_ADDRESS!
  const escrowAddress = process.env.NEXT_PUBLIC_ESCROW_ADDRESS!

  useEffect(() => {
    if (typeof window === 'undefined' || !(window as any).ethereum) {
      setError('Please install MetaMask.')
      return
    }

    // v5: use Web3Provider and explicitly disable ENS lookups on localhost
    const provider = new ethers.providers.Web3Provider(
      (window as any).ethereum,
      { name: 'localhost', chainId: 31337 }
    )

    // pop the “connect account” dialog
    provider
      .send('eth_requestAccounts', [])
      .then(() => {
        const signer = provider.getSigner()
        setTokenContract(
          new ethers.Contract(tokenAddress, (gluAbi as any).abi, signer)
        )
        setEscrowContract(
          new ethers.Contract(escrowAddress, (escrowAbi as any).abi, signer)
        )
      })
      .catch(() => {
        setError('Wallet connection failed')
      })
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
      // calculate GLU amount (1 GLU ≈ 1 USD)
      const amountGlu = ethers.utils.parseUnits(
        (qty * pricePerKg).toString(),
        18
      )

      // 1) Approve the escrow contract
      const approveTx = await tokenContract.approve(escrowAddress, amountGlu)
      await approveTx.wait()
        
      // 2) Create the on‑chain escrow
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
    <div className="p-4 border rounded bg-gray-50">
      <label className="block mb-2">
        Quantity (kg):
        <input
          type="number"
          value={qty || ''}
          onChange={e => setQty(parseFloat(e.target.value))}
          className="ml-2 p-1 border rounded w-20"
          min="0"
          step="0.01"
        />
      </label>
        
      <p className="mb-4">
        Total GLU: <strong>{(qty * pricePerKg).toFixed(2)} GLU</strong>
      </p>
      
      {error && <p className="text-red-600 mb-2">{error}</p>}
    
      <button
        onClick={handleDeposit}
        disabled={loading}
        className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
      >
        {loading ? 'Processing…' : 'Lock GLU in Escrow'}
      </button>
    </div>
  )
}

