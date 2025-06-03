/**
 * Shape of a “Deal” as returned by GET /deals/:id
 */
export interface Deal {
  id: number;
  product_title: string;
  quantity_kg: number;
  total_price: number;
  status: string;
  created_at: string;
  supplier_wallet_address?: string;
  // add any other fields your backend actually returns…
}
