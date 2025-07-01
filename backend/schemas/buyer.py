# backend/schemas/buyer.py

from pydantic import BaseModel

class BuyerDashboard(BaseModel):
    totalSalesToday: int
    openOrders:       int
    pendingEscrow:    int
    availableProducts:int
    activeDeals:      int