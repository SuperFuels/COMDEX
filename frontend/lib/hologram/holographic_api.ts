// File: frontend/lib/hologram/holographic_api.ts

import axios from "axios";
import { HolographicTree } from "../types/symbolic_types";  // ✅ Fixed relative path

/**
 * Fetches the symbolic meaning tree from the backend for a given container.
 */
export async function fetchHolographicTree(containerId: string): Promise<HolographicTree> {
  try {
    const response = await axios.get(`/api/qfc/holographic_tree/${containerId}`);
    return response.data.tree as HolographicTree;
  } catch (err) {
    console.error("Failed to fetch symbolic meaning tree:", err);
    throw err;
  }
}