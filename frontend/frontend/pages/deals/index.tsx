import { useEffect, useState } from 'react';
import axios from 'axios';
import Navbar from '@/components/Navbar';
import useAuthRedirect from '@/hooks/useAuthRedirect';
import { useRouter } from 'next/router';

interface Deal {
  id: number;
  product_title: string;
  buyer_email: string;
  supplier_email: string;
  quantity_kg: number;
  total_price: number;
  status: string;
}

export default function DealsPage() {
  const router = useRouter();
  const [deals, setDeals] = useState<Deal[]>([]);
  const [error, setError] = useState('');
  const [role, setRole] = useState('');
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  useAuthRedirect(); // Check if user is logged in

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    const fetchDeals = async () => {
      try {
        const roleRes = await axios.get('http://localhost:8000/auth/role', {
          headers: { Authorization: `Bearer ${token}` },
        });
        setRole(roleRes.data.role);

        const res = await axios.get('http://localhost:8000/deals/me', {
          headers: { Authorization: `Bearer ${token}` },
        });

        setDeals(res.data);
      } catch (err) {
        setError('❌ Failed to load deals');
      }
    };

    fetchDeals();
  }, []);

  const handleToggleStatus = async (dealId: number) => {
    const token = localStorage.getItem('token');
    try {
      await axios.patch(`http://localhost:8000/deals/${dealId}/status`, null, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const refreshed = await axios.get('http://localhost:8000/deals/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      setDeals(refreshed.data);
    } catch (err) {
      alert('❌ Failed to update status');
    }
  };

  const handlePDFDownload = async (dealId: number) => {
    const token = localStorage.getItem('token');
    try {
      const response = await axios.get(`http://localhost:8000/deals/${dealId}/pdf`, {
        responseType: 'blob',
        headers: { Authorization: `Bearer ${token}` },
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `deal_${dealId}.pdf`);
      document.body.appendChild(link);
      link.click();
    } catch (err) {
      alert('❌ Failed to download PDF');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="p-6 max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-4">My Deals</h1>
        {error && <p className="text-red-600 mb-4">{error}</p>}

        <div className="bg-white shadow rounded p-4 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr>
                <th className="text-left p-2">Product</th>
                <th className="text-left p-2">Buyer</th>
                <th className="text-left p-2">Supplier</th>
                <th className="text-left p-2">Qty (KG)</th>
                <th className="text-left p-2">Total $</th>
                <th className="text-left p-2">Status</th>
                <th className="text-left p-2">PDF</th>
              </tr>
            </thead>
            <tbody>
              {deals.map((d) => (
                <tr key={d.id} className="border-t">
                  <td className="p-2">{d.product_title}</td>
                  <td className="p-2">{d.buyer_email}</td>
                  <td className="p-2">{d.supplier_email}</td>
                  <td className="p-2">{d.quantity_kg}</td>
                  <td className="p-2">${d.total_price}</td>
                  <td className="p-2">
                    {role === 'supplier' ? (
                      <button
                        onClick={() => handleToggleStatus(d.id)}
                        className={`text-sm px-2 py-1 rounded ${
                          d.status === 'completed'
                            ? 'bg-green-500 text-white'
                            : 'bg-yellow-400 text-black'
                        }`}
                      >
                        {d.status === 'completed' ? 'Completed' : 'Mark Completed'}
                      </button>
                    ) : (
                      <span className="capitalize">{d.status}</span>
                    )}
                  </td>
                  <td className="p-2">
                    <button
                      onClick={() => handlePDFDownload(d.id)}
                      className="text-blue-600 underline hover:text-blue-800"
                    >
                      Download
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}

