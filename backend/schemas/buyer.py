# backend/schemas/buyer.py

from pydantic import BaseModel

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class BuyerDashboard(BaseModel):
    totalSalesToday: int
    openOrders:       int
    pendingEscrow:    int
    availableProducts:int
    activeDeals:      int