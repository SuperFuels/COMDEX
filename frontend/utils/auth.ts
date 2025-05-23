// frontend/utils/auth.ts

import api from '@/lib/api'

export const getToken = (): string | null => {
  return localStorage.getItem('token')
}

export const isAuthenticated = (): boolean => {
  return !!getToken()
}

export const logout = (): void => {
  localStorage.removeItem('token')
  delete api.defaults.headers.common.Authorization
  window.location.href = '/login'
}

/**
 * Performs the SIWE login flow:
 * 1) Requests a nonce/message from GET /auth/nonce
 * 2) Asks MetaMask to personal_sign()
 * 3) Sends message+signature to POST /auth/verify
 * 4) Stores the returned JWT and sets it on axios defaults
 */
export async function signInWithEthereum(): Promise<{ address: string; role: string }> {
  if (!(window as any).ethereum) {
    throw new Error('No Ethereum wallet detected')
  }

  // 1) get the user’s address
  const [address]: string[] = await (window as any).ethereum.request({
    method: 'eth_requestAccounts'
  })

  // 2) fetch nonce + SIWE message
  const { data: { message } } = await api.get('/auth/nonce', {
    params: { address }
  })

  // 3) ask wallet to sign it
  const signature: string = await (window as any).ethereum.request({
    method: 'personal_sign',
    params: [message, address]
  })

  // 4) verify on the backend
  const { data: { token, role } } = await api.post('/auth/verify', {
    message,
    signature
  })

  // 5) store + set auth header
  localStorage.setItem('token', token)
  api.defaults.headers.common.Authorization = `Bearer ${token}`

  return { address, role }
}


