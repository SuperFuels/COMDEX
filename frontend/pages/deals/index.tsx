import { useEffect, useState } from 'react';
import axios from 'axios';
import { useRouter } from 'next/router';
import useAuthRedirect from '../../hooks/useAuthRedirect'; // ✅ Protect page

interface Deal {
  id: number;
  buyer_email: string;
  supplier_email: string;
  product_title: string;
  quantity_kg: number;
  total_price: number;
  status: string;
  created_at: string;
}

export default function DealsPage() {
  useAuthRedirect(); // ✅ Redirects if not authenticated

  const [deals, setDeals] = useState<Deal[]>([]);
  const [filteredDeals, setFilteredDeals] = useState<Deal[]>([]);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    const fetchDeals = async () => {
      try {
        const response = await axios.get('http://localhost:8000/deals/', {
          headers: { Authorization: `Bearer ${token}` },
        });
        setDeals(response.data);
        setFilteredDeals(response.data);
      } catch (err: any) {
        console.error('Error fetching deals:', err);
        setError('Failed to load deals.');
      }
    };

    fetchDeals();
  }, [router]);

  useEffect(() => {
    const filtered = deals.filter((deal) =>
      deal.product_title.toLowerCase().includes(search.toLowerCase())
    );
    setFilteredDeals(filtered);
  }, [search, deals]);

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'confirmed':
        return 'text-green-600 font-semibold';
      case 'completed':
        return 'text-blue-600 font-semibold';
      default:
        return 'text-yellow-600 font-semibold';
    }
  };

  const handleStatusChange = async (dealId: number, newStatus: string) => {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
      await axios.put(
        `http://localhost:8000/deals/${dealId}/status`,
        { status: newStatus },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const updated = deals.map((d) =>
        d.id === dealId ? { ...d, status: newStatus } : d
      );
      setDeals(updated);
      setFilteredDeals(updated);
    } catch (err) {
      console.error('Failed to update deal status:', err);
      alert('Status update failed.');
    }
  };

  const handlePDFPreview = async (dealId: number) => {
    const token = localStorage.getItem('token');
    if (!token) {
      alert('Please log in to preview this PDF.');
      return;
    }

    try {
      const response = await axios.get(`http://localhost:8000/deals/${dealId}/pdf`, {
        responseType: 'blob',
        headers: { Authorization: `Bearer ${token}` },
      });

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      setPdfUrl(url);
    } catch (error) {
      console.error('❌ Failed to preview PDF:', error);
      alert('Failed to load PDF.');
    }
  };

  return (
    <main className="w-full p-6 bg-gray-100 min-h-screen">
      <h1 className="text-2xl font-bold mb-4">My Deals</h1>

      {error && <p className="text-red-500 mb-4">{error}</p>}

      <input
        type="text"
        placeholder="Filter by product title..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="mb-4 p-2 border border-gray-300 rounded w-full"
      />

      {filteredDeals.length === 0 ? (
        <p>No deals found.</p>
      ) : (
        <div className="space-y-4">
          {filteredDeals.map((deal) => (
            <div
              key={deal.id}
              className="bg-white p-4 rounded shadow flex justify-between items-start"
            >
              <div>
                <p className="font-semibold text-lg">{deal.product_title}</p>
                <p className="text-sm text-gray-600">
                  Buyer: {deal.buyer_email} | Supplier: {deal.supplier_email}
                </p>
                <p className="text-sm">Quantity: {deal.quantity_kg} kg</p>
                <p className="text-sm font-bold text-green-700">
                  Total: ${deal.total_price}
                </p>
                <p className="text-xs text-gray-500">
                  Created: {new Date(deal.created_at).toLocaleDateString()}
                </p>
                <p className={`text-xs mt-1 ${getStatusStyle(deal.status)}`}>
                  Status: {deal.status}
                </p>

                <div className="mt-2">
                  <label className="text-xs font-semibold mr-2">Update Status:</label>
                  <select
                    value={deal.status}
                    onChange={(e) => handleStatusChange(deal.id, e.target.value)}
                    className="text-sm p-1 border rounded"
                  >
                    <option value="negotiation">Negotiation</option>
                    <option value="confirmed">Confirmed</option>
                    <option value="completed">Completed</option>
                  </select>
                </div>
              </div>

              <button
                onClick={() => handlePDFPreview(deal.id)}
                className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
              >
                Preview PDF
              </button>
            </div>
          ))}
        </div>
      )}

      {pdfUrl && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-4 rounded shadow-lg max-w-3xl w-full">
            <div className="flex justify-between mb-2">
              <h2 className="text-lg font-semibold">PDF Preview</h2>
              <button
                onClick={() => setPdfUrl(null)}
                className="text-red-600 hover:text-red-800 text-sm"
              >
                Close ✖
              </button>
            </div>
            <iframe src={pdfUrl} className="w-full h-[500px]" />
          </div>
        </div>
      )}
    </main>
  );
}

