# backend/schemas/supplier.py

from typing import List
from pydantic import BaseModel

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