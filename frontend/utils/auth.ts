// frontend/utils/auth.ts
import { ethers } from 'ethers'
import api from '@/lib/api'              // ← your preconfigured axios instance
import { SiweMessage } from 'siwe'

/** helper to grab window.ethereum or throw */
function getEthereumProvider(): any {
  if (typeof window === 'undefined' || !(window as any).ethereum) {
    throw new Error(
      'No Ethereum provider found. Please install MetaMask or another wallet.'
    )
  }
  return (window as any).ethereum
}

/**
 * Perform a SIWE login:
 * 1. request accounts
 * 2. get chainId & nonce
 * 3. build & sign a SiweMessage
 * 4. POST { message, signature } to /auth/verify
 * 5. persist token & role, set axios header, bind wallet on profile
 */
export async function signInWithEthereum(): Promise<{
  address: string
  role:    string
}> {
  // 1) get provider & request accounts
  const eth = getEthereumProvider()
  const [rawAddress] = (await eth.request({
    method: 'eth_requestAccounts',
  })) as string[]

  // 2) checksum
  const address = ethers.utils.getAddress(rawAddress)

  // 3) fetch nonce (as JSON)
  const {
    data: { nonce },
  } = await api.get<{ nonce: string }>('/auth/nonce', {
    params: { address },
    withCredentials: true,
  })

  // 4) determine chain ID
  const chainHex = (await eth.request({ method: 'eth_chainId' })) as string
  const chainId  = parseInt(chainHex, 16)

  // 5) build the SIWE message
  const siweMessage = new SiweMessage({
    domain:    window.location.host,
    address,
    statement: 'Sign in with Ethereum to STICKEY',
    uri:       window.location.origin,
    version:   '1',
    chainId,
    nonce,
  })
  const message = siweMessage.prepareMessage()

  // 6) get the user’s signature
  const signature = (await eth.request({
    method: 'personal_sign',
    params: [message, address],
  })) as string

  // 7) POST message+signature to verify endpoint
  const {
    data: { token, user },
  } = await api.post<{
    token: string
    user:  { role: string }
  }>(
    '/auth/verify',
    { message, signature },
    { withCredentials: true }
  )

  // 8) persist JWT + role in localStorage
  localStorage.setItem('token', token)
  localStorage.setItem('role', user.role)

  // 9) ensure axios sends it from now on
  api.defaults.headers.common.Authorization = `Bearer ${token}`

  // 10) optionally bind this wallet on the server
  await api.patch('/users/me/wallet', {
    wallet_address: address,
  })

  return { address, role: user.role }
}

/** Helpers for other parts of your app */
export const getToken        = (): string | null => localStorage.getItem('token')
export const getRole         = (): string | null => localStorage.getItem('role')
export const isAuthenticated = (): boolean      => Boolean(getToken())

/** Logout by clearing storage & reloading */
export function logout(): void {
  localStorage.removeItem('token')
  localStorage.removeItem('role')
  // optional: track manual disconnect
  localStorage.setItem('manualDisconnect', 'true')
  // force reload so isAuthenticated() flips to false
  window.location.reload()
}