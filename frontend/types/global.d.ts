// global.d.ts
import type { MetaMaskInpageProvider } from "@metamask/providers";

declare global {
  interface Window {
    /** injected by MetaMask/EIP-1193 wallets */
    ethereum?: MetaMaskInpageProvider & {
      /** legacy alias */
      selectedAddress?: string;
    };
  }
}
