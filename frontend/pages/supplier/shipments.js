import { useEffect, useState } from 'react';

export default function SupplierShipments() {
  const [shipments, setShipments] = useState([]);

  useEffect(() => {
    fetch('/api/shipments')
      .then((res) => res.json())
      .then(setShipments)
      .catch(console.error);
  }, []);

  return (
    <div style={{ padding: '2rem' }}>
      <h1>My Shipments</h1>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Deal</th>
            <th>Product</th>
            <th>Qty (kg)</th>
            <th>Shipped At</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {shipments.map((s) => (
            <tr key={s.id}>
              <td>{s.id}</td>
              <td>{s.deal_id}</td>
              <td>{s.product_id ?? '—'}</td>
              <td>{s.quantity_kg}</td>
              <td>{new Date(s.shipped_at).toLocaleString()}</td>
              <td>{s.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
