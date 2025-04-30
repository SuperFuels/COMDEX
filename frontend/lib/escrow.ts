import { ethers } from 'ethers';
import EscrowABI from '../contracts/Escrow.json';// Adjusted path if it's not resolving with alias

// ✅ Deployed contract address on Polygon Amoy
const ESCROW_CONTRACT_ADDRESS = '0xC4e695966B04fB8ee57d09Fa39A81a8b9582279b';

/**
 * Returns an instance of the escrow contract
 */
export function getEscrowContract(signerOrProvider: ethers.Signer | ethers.Provider) {
  return new ethers.Contract(ESCROW_CONTRACT_ADDRESS, EscrowABI, signerOrProvider);
}

/**
 * Buyer calls this to release funds to the seller
 */
export async function releaseToSeller(signer: ethers.Signer) {
  const contract = getEscrowContract(signer);
  const tx = await contract.releaseToSeller();
  return await tx.wait();
}

/**
 * Seller calls this to refund buyer
 */
export async function refundToBuyer(signer: ethers.Signer) {
  const contract = getEscrowContract(signer);
  const tx = await contract.refundToBuyer();
  return await tx.wait();
}

/**
 * Anyone can view current balance of the escrow contract
 */
export async function getEscrowBalance(provider: ethers.Provider) {
  const contract = getEscrowContract(provider);
  return await contract.getBalance();
}

