import { useState } from 'react';
import useEscrowContract from '@/hooks/useEscrowContract';

export default function EscrowActions() {
  const escrow = useEscrowContract();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleReleaseToSeller = async () => {
    if (!escrow) return;
    try {
      setLoading(true);
      const tx = await escrow.releaseToSeller();
      await tx.wait();
      setMessage('✅ Funds released to Seller!');
    } catch (err: any) {
      console.error(err);
      setMessage('❌ Transaction failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRefundToBuyer = async () => {
    if (!escrow) return;
    try {
      setLoading(true);
      const tx = await escrow.refundToBuyer();
      await tx.wait();
      setMessage('✅ Funds refunded to Buyer!');
    } catch (err: any) {
      console.error(err);
      setMessage('❌ Transaction failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center gap-4">
      <button
        onClick={handleReleaseToSeller}
        disabled={loading}
        className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
      >
        Release Funds to Seller
      </button>

      <button
        onClick={handleRefundToBuyer}
        disabled={loading}
        className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 disabled:opacity-50"
      >
        Refund Buyer
      </button>

      {message && <p className="text-center mt-2">{message}</p>}
    </div>
  );
}

