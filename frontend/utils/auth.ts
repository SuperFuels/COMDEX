// frontend/utils/auth.ts

import { ethers } from 'ethers'
import api from '@/lib/api'
import { SiweMessage } from 'siwe'

/** Grabs window.ethereum or throws if missing */
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
 *  1) request accounts
 *  2) fetch nonce
 *  3) build & sign a SiweMessage
 *  4) POST { message, signature } to /auth/verify
 *  5) persist JWT + role, set axios header, bind wallet
 *
 * @returns the connected address and your user role
 */
export async function signInWithEthereum(): Promise<{
  address: string
  role:    string
}> {
  // 1) request accounts
  const eth = getEthereumProvider()
  const [rawAddress] = (await eth.request({
    method: 'eth_requestAccounts',
  })) as string[]
  const address = ethers.utils.getAddress(rawAddress)

  // 2) fetch nonce from backend
  const {
    data: { nonce },
  } = await api.get<{ nonce: string }>('/auth/nonce', {
    params: { address },
    withCredentials: true,
  })

  // 3) determine chain ID
  const chainHex = (await eth.request({ method: 'eth_chainId' })) as string
  const chainId  = parseInt(chainHex, 16)

  // 4) build the SIWE message
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

  // 5) have user sign the message
  const signature = (await eth.request({
    method: 'personal_sign',
    params: [message, address],
  })) as string

  // 6) verify with backend, receive JWT + user.role
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

  // 7) persist JWT & role, configure axios
  localStorage.setItem('token', token)
  localStorage.setItem('role',  user.role)
  api.defaults.headers.common.Authorization = `Bearer ${token}`

  // 8) bind/update your wallet on your profile (optional)
  try {
    await api.patch(
      '/users/me/wallet',
      { wallet_address: address },
      { withCredentials: true }
    )
  } catch {
    // if that endpoint isn’t present yet, just ignore
  }

  // now return both address and role
  return { address, role: user.role }
}

/** Helpers for other parts of your app */
export const getToken        = (): string | null => localStorage.getItem('token')
export const getRole         = (): string | null => localStorage.getItem('role')
export const isAuthenticated = (): boolean      => Boolean(getToken())

/** Clears storage & reloads to force logout */
export function logout(): void {
  localStorage.removeItem('token')
  localStorage.removeItem('role')
  localStorage.setItem('manualDisconnect', 'true')
  window.location.reload()
}