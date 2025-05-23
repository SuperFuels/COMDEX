// frontend/utils/auth.ts

import axios from 'axios'
import { SiweMessage } from 'siwe'

const API = process.env.NEXT_PUBLIC_API_URL!

function getEthereumProvider() {
  if (typeof window === 'undefined' || !window.ethereum) {
    throw new Error('No Ethereum provider found. Install MetaMask or similar.')
  }
  return window.ethereum
}

export async function signInWithEthereum(): Promise<{ address: string; role: string }> {
  const eth = getEthereumProvider()

  // 1) get wallet address
  const [address] = (await eth.request({ method: 'eth_requestAccounts' })) as string[]

  // 2) fetch a nonce from your backend
  const { data: { nonce } } = await axios.get<{ nonce: string }>(
    `${API}/auth/nonce?address=${address}`
  )

  // 3) build the SIWE message
  const chainHex = await eth.request({ method: 'eth_chainId' })
  const chainId = parseInt(chainHex.toString(), 16)

  const siwe = new SiweMessage({
    domain:    window.location.host,
    address,
    statement: 'Sign in with Ethereum to Sticky',
    uri:       window.location.origin,
    version:   '1',
    chainId,
    nonce,
  })

  // 4) have the user sign it
  const message   = siwe.prepareMessage()
  const signature = (await eth.request({
    method: 'personal_sign',
    params: [message, address],
  })) as string

  // 5) POST to verify & get your JWT + user info
  const { data: { token, user } } = await axios.post<{
    token: string
    user:  { role: string }
  }>(
    `${API}/auth/verify`,
    { message, signature },
    { withCredentials: true }
  )

  // 6) persist token + role, clear manualDisconnect so auto-connect works again
  localStorage.setItem('token', token)
  localStorage.setItem('role',  user.role)
  localStorage.removeItem('manualDisconnect')

  return { address, role: user.role }
}

export const getToken       = (): string | null  => localStorage.getItem('token')
export const isAuthenticated = (): boolean       => Boolean(getToken())

export function logout(): void {
  localStorage.removeItem('token')
  localStorage.removeItem('role')
  localStorage.setItem('manualDisconnect', 'true')
  window.location.reload()
}
