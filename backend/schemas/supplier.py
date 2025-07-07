# backend/schemas/supplier.py

from typing import List
from pydantic import BaseModel

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class SupplierProductSummary(BaseModel):
    id:              int
    title:           str
    description:     str
    price_per_kg:    float
    origin_country:  str
    image_url:       str

class SupplierDashboard(BaseModel):
    totalSalesToday: int
    activeListings:  int
    openOrders:      int
    proceeds30d:     float
    feedbackRating:  float
    products:        List[SupplierProductSummary]