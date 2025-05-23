// global.d.ts
import type { MetaMaskInpageProvider } from "@metamask/providers";

declare global {
  interface Window {
    /** injected by MetaMask and other EIP-1193 wallets */
    ethereum?: MetaMaskInpageProvider & {
      /** legacy convenience prop; may be undefined */
      selectedAddress?: string;
    };
  }
}
