// frontend/lib/escrow.ts

import { ethers } from 'ethers'
import EscrowArtifact from '../contracts/Escrow.json'  // the full JSON artifact

// ✅ Deployed contract address on Polygon Amoy
const ESCROW_CONTRACT_ADDRESS = '0xC4e695966B04fB8ee57d09Fa39A81a8b9582279b'

/**
 * Returns an instance of the escrow contract
 */
export function getEscrowContract(
  signerOrProvider: ethers.Signer | ethers.Provider
): ethers.Contract {
  return new ethers.Contract(
    ESCROW_CONTRACT_ADDRESS,
    EscrowArtifact.abi,    // ← use the ABI array, not the whole JSON
    signerOrProvider
  )
}

/**
 * Buyer calls this to release funds to the seller
 */
export async function releaseToSeller(
  signer: ethers.Signer
): Promise<ethers.ContractTransactionReceipt> {
  const contract = getEscrowContract(signer)
  const tx = await contract.releaseToSeller()
  const receipt = await tx.wait()
  if (!receipt) throw new Error('Transaction was not mined')
  return receipt
}

/**
 * Seller calls this to refund buyer
 */
export async function refundToBuyer(
  signer: ethers.Signer
): Promise<ethers.ContractTransactionReceipt> {
  const contract = getEscrowContract(signer)
  const tx = await contract.refundToBuyer()
  const receipt = await tx.wait()
  if (!receipt) throw new Error('Transaction was not mined')
  return receipt
}

/**
 * Anyone can view current balance of the escrow contract
 */
export async function getEscrowBalance(
  provider: ethers.Provider
): Promise<bigint> {
  const contract = getEscrowContract(provider)
  return contract.getBalance()
}

export const ESCROW_ABI = EscrowArtifact.abi;
export { ESCROW_CONTRACT_ADDRESS };
