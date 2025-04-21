// components/WalletConnect.tsx
import { useState } from 'react';

export default function WalletConnect() {
  const [walletAddress, setWalletAddress] = useState<string | null>(null);

  const connectWallet = async () => {
    if (typeof window.ethereum !== 'undefined') {
      try {
        const accounts = await window.ethereum.request({
          method: 'eth_requestAccounts',
        });
        setWalletAddress(accounts[0]);
      } catch (err) {
        alert('🛑 Wallet connection failed');
        console.error(err);
      }
    } else {
      alert('🦊 MetaMask not detected');
    }
  };

  return (
    <div className="text-center mt-4">
      {walletAddress ? (
        <p className="text-green-600 font-mono">🔗 {walletAddress}</p>
      ) : (
        <button
          onClick={connectWallet}
          className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
        >
          Connect Wallet
        </button>
      )}
    </div>
  );
}

