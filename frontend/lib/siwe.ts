// frontend/lib/siwe.ts
import { ethers } from 'ethers'
import { SiweMessage } from 'siwe'
import api from './api'

export interface LoginResult {
  token: string
  role: string
}

export async function signInWithEthereum(): Promise<LoginResult> {
  if (!(window as any).ethereum) {
    throw new Error('No injected Ethereum provider found')
  }

  const provider = new ethers.providers.Web3Provider(
    (window as any).ethereum,
    'any'
  )
  await provider.send('eth_requestAccounts', [])
  const signer = provider.getSigner()
  const address = await signer.getAddress()

  // 1) Fetch nonce
  const {
    data: { nonce },
  } = await api.get<{ nonce: string }>(
    `/auth/nonce?address=${address}`
  )

  // 2) Build SIWE message
  const siweMessage = new SiweMessage({
    domain: window.location.host,
    address,
    statement: 'Sign in to STICKEY',
    uri: window.location.origin,
    version: '1',
    chainId: 1,
    nonce,
  })
  const message = siweMessage.prepareMessage()

  // 3) Sign it
  const signature = await signer.signMessage(message)

  // 4) Verify & receive JWT + role
  const { data } = await api.post<LoginResult>(
    '/auth/verify',
    { message, signature },
    { withCredentials: true }
  )

  return data
}