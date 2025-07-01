/**
 * ANY time your code says `import { Deal } from '@/types'`,
 * TypeScript will look in this file for an exported `Deal` interface.
 * Adjust these properties to match exactly what your backend returns.
 */
export interface Deal {
  id: number;
  product_title: string;
  status: string;
  amount?: number;
  // … add any other fields your front-end code expects from a Deal …
}
