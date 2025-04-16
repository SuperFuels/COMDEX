"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUserDeals } from "@/lib/api";
import Link from "next/link";
import Header from "@/components/Header";
import withAuth from "@/lib/withAuth";

function DealsPage() {
  const [deals, setDeals] = useState([]);
  const router = useRouter();

  useEffect(() => {
    async function fetchDeals() {
      try {
        const res = await getUserDeals();
        setDeals(res);
      } catch (err) {
        console.error("Failed to fetch deals", err);
        router.push("/login");
      }
    }
    fetchDeals();
  }, []);

  return (
    <>
      <Header />
      <main className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">🤝 Your Deals</h1>
        </div>

        {deals.length === 0 ? (
          <p className="text-gray-400">You haven’t made any deals yet.</p>
        ) : (
          <div className="space-y-4">
            {deals.map((deal: any) => (
              <div
                key={deal.id}
                className="bg-white text-black p-4 rounded shadow-md"
              >
                <p>
                  <strong>Product:</strong> {deal.product_title}
                </p>
                <p>
                  <strong>Quantity:</strong> {deal.quantity_kg} kg
                </p>
                <p>
                  <strong>Price:</strong> ${deal.agreed_price} {deal.currency}
                </p>
                <p>
                  <strong>Seller:</strong> {deal.seller_email}
                </p>
                <Link
                  href={`/deals/${deal.id}/pdf`}
                  className="text-blue-600 underline mt-2 inline-block"
                >
                  📄 Download PDF
                </Link>
              </div>
            ))}
          </div>
        )}
      </main>
    </>
  );
}

export default withAuth(DealsPage);

