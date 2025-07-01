import { ethers } from 'ethers'
import api from '@/lib/api'

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
 *  2) fetch full SIWE message from your backend
 *  3) ask user to sign that message
 *  4) POST { message, signature } to /auth/verify
 *  5) persist JWT (under "token") & role, set axios header, bind wallet
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

  // 2) fetch the full SIWE message from your backend
  const { data: { message } } = await api.get<{ message: string }>(
    '/auth/nonce',
    { params: { address }, withCredentials: true }
  )

  // 2.1) log the exact SIWE payload for debugging
  console.debug('SIWE nonce fetched:', message)

  // 3) have user sign exactly that message
  const signature = (await eth.request({
    method: 'personal_sign',
    params: [message, address],
  })) as string

  // 4) send back message+signature for verification
  const { data: { token, role } } = await api.post<{
    token: string
    role:  string
  }>(
    '/auth/verify',
    { message, signature },
    { withCredentials: true }
  )

  // 5) persist JWT & role, configure axios
  localStorage.setItem('token', token)
  localStorage.setItem('role',  role)
  api.defaults.headers.common['Authorization'] = `Bearer ${token}`

  // 6) attempt to bind/update your wallet on your profile (optional)
  try {
    await api.patch(
      '/users/me/wallet',
      { wallet_address: address },
      { withCredentials: true }
    )
  } catch {
    // ignore if that endpoint isn’t available yet
  }

  return { address, role }
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
