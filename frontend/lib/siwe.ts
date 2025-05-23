// frontend/lib/siwe.ts
import { SiweMessage } from "siwe";
import api from "./api";

export async function signInWithEthereum(): Promise<string> {
  // 1) check wallet
  if (!window.ethereum) {
    throw new Error("No Ethereum wallet detected");
  }

  // 2) request access to accounts
  const accounts: string[] = await window.ethereum.request({
    method: "eth_requestAccounts",
  });
  const address = accounts[0];
  if (!address) {
    throw new Error("No account found");
  }

  // 3) fetch a fresh nonce
  const {
    data: { message: nonceMessage },
  } = await api.get<{ message: string }>(`/auth/nonce?address=${address}`);

  // 4) build the SIWE message
  const siweMsg = new SiweMessage({
    domain: window.location.host,
    address,
    statement: "Sign in to COMDEX",
    uri: window.location.origin,
    version: "1",
    chainId: 1,
    nonce: nonceMessage,
  });
  const messageToSign = siweMsg.prepareMessage();

  // 5) have user sign
  const signature: string = await window.ethereum.request({
    method: "personal_sign",
    params: [messageToSign, address],
  });

  // ←— debug logging
  console.log("→ verify payload:", { message: messageToSign, signature });

  // 6) send to your backend
  const { data } = await api.post<{ token: string }>(
    "/auth/verify",
    { message: messageToSign, signature },
    { withCredentials: true }
  );

  return data.token;
}
