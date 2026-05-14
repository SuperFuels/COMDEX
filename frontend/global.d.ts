// frontend/global.d.ts
import type { MetaMaskInpageProvider } from "@metamask/providers";

declare global {
  interface Window {
    /** injected by MetaMask and other EIP-1193 wallets */
    ethereum?: MetaMaskInpageProvider & {
      /** legacy convenience prop; may be undefined */
      selectedAddress?: string;

      /**
       * Generic request method.
       * @param args.method the RPC method name
       * @param args.params optional array of params for the method
       * @returns a promise resolving to whatever T the caller expects
       */
      request<T = unknown>(args: { method: string; params?: unknown[] }): Promise<T>;

      /** subscribe to provider events (accountsChanged, chainChanged, etc.) */
      on(event: string | symbol, listener: (...args: any[]) => void): this;

      /** remove a specific listener */
      removeListener(event: string | symbol, listener: (...args: any[]) => void): this;
    };
  }
}

// Ensure this file is treated as a module
export {};