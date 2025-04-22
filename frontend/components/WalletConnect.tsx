import { useState } from 'react';
import axios from 'axios';

export default function WalletConnect() {
  const [walletAddress, setWalletAddress] = useState<string | null>(null);

  const connectWallet = async () => {
    if (typeof window.ethereum !== 'undefined') {
      try {
        const accounts = await window.ethereum.request({
          method: 'eth_requestAccounts',
        });
        const address = accounts[0];
        setWalletAddress(address);

        const token = localStorage.getItem('token');
        if (!token) {
          alert('🔐 Please log in first to bind your wallet');
          return;
        }

        await axios.patch(
          'http://localhost:8000/users/me/wallet',
          { wallet_address: address },
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        console.log('✅ Wallet successfully linked to user account');
      } catch (err) {
        alert('🛑 Wallet connection failed');
        console.error('Wallet Connect Error:', err);
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

