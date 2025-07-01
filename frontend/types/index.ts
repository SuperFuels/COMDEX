// frontend/types/index.ts
// ────────────────────────────────────────────────────────────────────────────
// This file defines the shape of a “Deal” exactly as your backend returns it.
// Adjust field names/types if your API returns something different.
// ────────────────────────────────────────────────────────────────────────────

export interface Deal {
  id: number;
  product_id: number;
  product_title: string;
  quantity_kg: number;
  total_price: number;
  status: 'negotiation' | 'confirmed' | 'completed' | 'cancelled';
  supplier_wallet_address: string | null;
  created_at: string;
  // (Add any other fields your API returns here)
}