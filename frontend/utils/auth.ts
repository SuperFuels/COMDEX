// frontend/utils/auth.ts
import { ethers } from 'ethers'
import api from '@/lib/api'              // ← your preconfigured axios instance
import { SiweMessage } from 'siwe'

const API = process.env.NEXT_PUBLIC_API_URL!

function getEthereumProvider(): any {
  if (typeof window === 'undefined' || !window.ethereum) {
    throw new Error('No Ethereum provider found. Install MetaMask or similar.')
  }
  return window.ethereum
}

export async function signInWithEthereum(): Promise<{ address: string; role: string }> {
  const eth = getEthereumProvider()

  // 1) request accounts
  const [rawAddress] = (await eth.request({ method: 'eth_requestAccounts' })) as string[]

  // 2) checksum it (throws if invalid)
  const address = ethers.utils.getAddress(rawAddress)

  // 3) fetch SIWE nonce
  const { data: { nonce } } = await api.get<{ nonce: string }>(
    `/auth/nonce?address=${address}`
  )

  // 4) build message
  const chainHex = (await eth.request({ method: 'eth_chainId' })) as string
  const chainId  = parseInt(chainHex, 16)
  const siwe = new SiweMessage({
    domain:    window.location.host,
    address,
    statement: 'Sign in with Ethereum to Sticky',
    uri:       window.location.origin,
    version:   '1',
    chainId,
    nonce,
  })

  // 5) sign it
  const message   = siwe.prepareMessage()
  const signature = (await eth.request({
    method: 'personal_sign',
    params: [message, address],
  })) as string

  // 6) verify & get JWT + role
  const { data: { token, user } } = await api.post<{
    token: string
    user:  { role: string }
  }>(
    `/auth/verify`,
    { message, signature },
    { withCredentials: true }
  )

  // 7) persist + clear manualDisconnect
  localStorage.setItem('token', token)
  localStorage.setItem('role',  user.role)
  localStorage.removeItem('manualDisconnect')

  // 8) set axios header so subsequent calls carry your JWT
  api.defaults.headers.common.Authorization = `Bearer ${token}`

  // 9) bind/update your wallet on your user profile
  await api.patch('/users/me/wallet', { wallet_address: address })

  return { address, role: user.role }
}

export const getToken        = (): string | null => localStorage.getItem('token')
export const isAuthenticated = (): boolean      => Boolean(getToken())

export function logout(): void {
  localStorage.removeItem('token')
  localStorage.removeItem('role')
  localStorage.setItem('manualDisconnect', 'true')
  window.location.reload()
}