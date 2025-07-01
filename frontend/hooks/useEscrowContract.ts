import { useMemo } from 'react';
import { ethers } from 'ethers';
import { ESCROW_ABI, ESCROW_CONTRACT_ADDRESS } from '@/constants/escrow';

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

