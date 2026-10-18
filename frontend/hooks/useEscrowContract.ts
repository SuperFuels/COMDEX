// File: frontend/hooks/useEscrowContract.ts

import { useEffect, useState } from 'react';
import { ethers } from 'ethers';
import {
  getEscrowContract,
  ESCROW_CONTRACT_ADDRESS,
  ESCROW_ABI
} from '@/lib/escrow'; // ✅ Correct path

export default function useEscrowContract() {
  const [contract, setContract] = useState<ethers.Contract | null>(null);

  useEffect(() => {
    let active = true;

    async function connect() {
      if (typeof window === 'undefined') return;
      const { ethereum } = window as any;
      if (!ethereum) {
        console.error('MetaMask not found');
        return;
      }

      const provider = new ethers.BrowserProvider(ethereum);
      const signer = await provider.getSigner();
      if (active) {
        setContract(
          new ethers.Contract(ESCROW_CONTRACT_ADDRESS, ESCROW_ABI, signer)
        );
      }
    }

    connect().catch((error) => {
      console.error('Could not connect escrow contract', error);
      if (active) setContract(null);
    });

    return () => {
      active = false;
    };
  }, []);

  return contract;
}
