// frontend/lib/siwe.ts
import { ethers } from 'ethers'
import { SiweMessage } from 'siwe'
import api from './api'

export interface LoginResult {
  token: string
  role:  string
}

export async function signInWithEthereum(): Promise<LoginResult> {
  if (!(window as any).ethereum) {
    throw new Error('No injected Ethereum provider found')
  }

  // 1) connect wallet
  const provider = new ethers.providers.Web3Provider(
    (window as any).ethereum,
    'any'
  )
  await provider.send('eth_requestAccounts', [])
  const signer  = provider.getSigner()
  const address = await signer.getAddress()

  // 2) get nonce
  const { data: { nonce } } = await api.get<{ nonce: string }>(
    `/auth/nonce?address=${address}`
  )

  // 3) build SIWE message
  const siweMessage = new SiweMessage({
    domain:  window.location.host,
    address,
    statement: 'Sign in to STICKEY',
    uri:     window.location.origin,
    version: '1',
    chainId: 1,
    nonce,
  })
  const message   = siweMessage.prepareMessage()

  // 4) sign it
  const signature = await signer.signMessage(message)

  // 5) verify on backend
  const { data } = await api.post<LoginResult>(
    '/auth/verify',
    { message, signature },
    { withCredentials: true }
  )

  // 6) persist & configure axios
  localStorage.setItem('token', data.token)
  localStorage.setItem('role',  data.role)
  api.defaults.headers.common.Authorization = `Bearer ${data.token}`

  // 7) bind wallet to profile (optional)
  await api.patch('/users/me/wallet', { wallet_address: address })

  return data
}