// File: frontend/hooks/useEscrowContract.ts

import { useMemo } from 'react';
import { ethers } from 'ethers';
import {
  getEscrowContract,
  ESCROW_CONTRACT_ADDRESS,
  ESCROW_ABI
} from '@/lib/escrow'; // ✅ Correct path

export default function useEscrowContract() {
  const getContract = () => {
    if (typeof window === 'undefined') return null;
    const { ethereum } = window as any;
    if (!ethereum) {
      console.error('MetaMask not found');
      return null;
    }
    const provider = new ethers.providers.Web3Provider(ethereum);
    const signer = provider.getSigner();
    return new ethers.Contract(ESCROW_CONTRACT_ADDRESS, ESCROW_ABI, signer);
  };

  return useMemo(() => getContract(), []);
}