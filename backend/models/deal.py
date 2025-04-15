from sqlalchemy import Column, Integer, String, Float
from database import Base

class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    buyer_email = Column(String, nullable=False)
    supplier_email = Column(String, nullable=False)
    product_title = Column(String, nullable=False)
    quantity_kg = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

