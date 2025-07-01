/**
 * Tell TS about window.ethereum
 */
export {}  // keep this file a module
declare global {
  interface Window {
    ethereum?: {
      request(args: { method: string; params?: any[] }): Promise<any>
      on?(event: string, handler: (...args: any[]) => void): void
      removeListener?(event: string, handler: (...args: any[]) => void): void
    }
  }
}
