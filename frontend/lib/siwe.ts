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
  const provider = new ethers.providers.Web3Provider(
    (window as any).ethereum,
    'any'
  )
  await provider.send('eth_requestAccounts', [])
  const signer  = provider.getSigner()
  const address = await signer.getAddress()

  // 2) Fetch the full SIWE message from backend
  const {
    data: { message: siweMessageString },
  } = await api.get<{ message: string }>(
    '/auth/nonce',
    {
      params: { address },
      withCredentials: true,
    }
  )

  // 3) Extract the nonce out of that message text
  const nonceLine = siweMessageString
    .split('\n')
    .find(line => line.trim().startsWith('Nonce:'))

  if (!nonceLine) {
    throw new Error('SIWE message from server did not include a Nonce')
  }
  const nonce = nonceLine.split('Nonce:')[1].trim()

  // 4) Build the SIWE message model
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
  const preparedMessage = siweMessage.prepareMessage()

  // 5) Have the user sign it
  const signature = await signer.signMessage(preparedMessage)

  // 6) Send to backend to verify & receive { token, role }
  const {
    data: { token, role },
  } = await api.post<LoginResult>(
    '/auth/verify',
    { message: preparedMessage, signature },
    { withCredentials: true }
  )

  // 7) Persist the JWT + role and set Axios header
  localStorage.setItem('token', token)
  localStorage.setItem('role',  role)
  api.defaults.headers.common.Authorization = `Bearer ${token}`

  // 8) (Optional) bind wallet on profile—ignore errors
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