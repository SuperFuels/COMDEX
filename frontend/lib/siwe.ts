// frontend/lib/siwe.ts

import api from './api'
import { SiweMessage } from 'siwe'
import { ethers } from 'ethers'

export async function signInWithEthereum(): Promise<string> {
  // 1) get a Web3 provider and prompt user to connect their wallet
  const provider = new ethers.providers.Web3Provider(window.ethereum as any)
  await provider.send('eth_requestAccounts', [])
  const signer = provider.getSigner()
  const address = await signer.getAddress()

  // 2) ask your backend for a nonce
  const {
    data: { nonce },
  } = await api.get<{ nonce: string }>(`/auth/nonce?address=${address}`)

  // 3) build a SIWE message
  const siweMessage = new SiweMessage({
    domain: window.location.host,
    address,
    statement: 'Sign in to COMDEX',
    uri: window.location.origin,
    version: '1',
    chainId: 1,
    nonce,
  })
  const messageToSign = siweMessage.prepareMessage()

  // 4) have the user sign it
  const signature = await signer.signMessage(messageToSign)

  // 5) send signed message + signature to your /auth/verify endpoint
  const resp = await api.post<{ token: string }>('/auth/verify', {
    message: messageToSign,
    signature,
  })

  const token = resp.data.token
  // 6) persist for next page load
  localStorage.setItem('jwt', token)
  return token
}
