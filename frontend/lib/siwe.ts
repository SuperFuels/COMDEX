// frontend/lib/siwe.ts
import { SiweMessage } from "siwe";
import api from "./api";

export async function signInWithEthereum(): Promise<string> {
  // 1) check wallet
  if (!window.ethereum) {
    throw new Error("No Ethereum wallet detected");
  }

  // 2) request access to accounts and cast to string[]
  const accounts = (await window.ethereum.request({
    method: "eth_requestAccounts",
  })) as string[];

  if (!accounts || accounts.length === 0) {
    throw new Error("No accounts returned from wallet");
  }
  const address = accounts[0];

  // 3) fetch a fresh nonce
  const {
    data: { message: nonceMessage },
  } = await api.get<{ message: string }>(`/auth/nonce?address=${address}`);

  // 4) build the SIWE message
  const siweMsg = new SiweMessage({
    domain: window.location.host,
    address,                    // now guaranteed to be a string
    statement: "Sign in to COMDEX",
    uri: window.location.origin,
    version: "1",
    chainId: 1,
    nonce: nonceMessage,
  });
  const messageToSign = siweMsg.prepareMessage();

  // 5) have user sign, cast to string
  const signature = (await window.ethereum.request({
    method: "personal_sign",
    params: [messageToSign, address],
  })) as string;

  if (!signature) {
    throw new Error("Signature request failed");
  }

  console.log("→ verify payload:", { message: messageToSign, signature });

  // 6) send to your backend
  const { data } = await api.post<{ token: string }>(
    "/auth/verify",
    { message: messageToSign, signature },
    { withCredentials: true }
  );

  return data.token;
}