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

  // 2) fetch SIWE nonce
  const { data: { nonce } } = await api.get<{ nonce: string }>(
    `/auth/nonce`,
    { params: { address }, withCredentials: true }
  )

  // 3) build message
  const siweMessage = new SiweMessage({
    domain:    window.location.host,
    address,
    statement: 'Sign in with Ethereum to STICKEY',
    uri:       window.location.origin,
    version:   '1',
    chainId:   parseInt(await provider.send('eth_chainId', []), 16),
    nonce,
  })
  const message = siweMessage.prepareMessage()

  // 4) sign
  const signature = await signer.signMessage(message)

  // 5) verify & receive JWT + role
  const {
    data: { token, role }
  } = await api.post<LoginResult>(
    '/auth/verify',
    { message, signature },
    { withCredentials: true }
  )

  // 6) persist + set header
  localStorage.setItem('token', token)
  localStorage.setItem('role',  role)
  api.defaults.headers.common.Authorization = `Bearer ${token}`

  // 7) bind wallet on profile
  await api.patch('/users/me/wallet', { wallet_address: address })

  return { token, role }
}