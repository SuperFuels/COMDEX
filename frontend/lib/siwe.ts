// frontend/lib/siwe.ts
import { ethers } from 'ethers'
import { SiweMessage } from 'siwe'
import api from '@/lib/api'

export interface LoginResult {
  token: string
  role:  string
}

export async function signInWithEthereum(): Promise<LoginResult> {
  if (!(window as any).ethereum) {
    throw new Error('No injected Ethereum provider found')
  }

  // 1) Connect wallet
  const provider = new ethers.providers.Web3Provider((window as any).ethereum, 'any')
  await provider.send('eth_requestAccounts', [])
  const signer  = provider.getSigner()
  const address = await signer.getAddress()

  // 2) Fetch SIWE nonce
  const {
    data: { nonce },
  } = await api.get<{ nonce: string }>(
    '/auth/nonce',
    {
      params: { address },
      withCredentials: true,
    }
  )

  // 3) Build the SIWE message
  const chainHex = await provider.send('eth_chainId', [])
  const siweMessage = new SiweMessage({
    domain:    window.location.host,
    address,
    statement: 'Sign in with Ethereum to STICKEY',
    uri:       window.location.origin,
    version:   '1',
    chainId:   parseInt(chainHex as string, 16),
    nonce,
  })
  const message = siweMessage.prepareMessage()

  // 4) Have the user sign it
  const signature = await signer.signMessage(message)

  // 5) Send to backend to verify & receive JWT + role
  const {
    data: { token, role },
  } = await api.post<LoginResult>(
    '/auth/verify',
    { message, signature },
    { withCredentials: true }
  )

  // 6) Persist and configure axios
  localStorage.setItem('token', token)
  localStorage.setItem('role',  role)
  api.defaults.headers.common.Authorization = `Bearer ${token}`

  // 7) (Optional) Bind wallet on your profile—ignore failures here
  try {
    await api.patch(
      '/users/me/wallet',
      { wallet_address: address },
      { withCredentials: true }
    )
  } catch (e) {
    console.warn('Could not bind wallet on profile:', e)
  }

  return { token, role }
}