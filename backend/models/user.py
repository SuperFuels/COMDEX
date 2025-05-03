# backend/models/User.py

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String, nullable=False, index=True)
    email          = Column(String, unique=True, index=True, nullable=False)
    password_hash  = Column(String, nullable=False)
    role           = Column(String, default="user", nullable=False)  # buyer, supplier, admin
    wallet_address = Column(String, nullable=True)                  # e.g. MetaMask address

    # Products owned by this user (if supplier)
    products = relationship(
        "Product",
        back_populates="owner",
        cascade="all, delete-orphan"
    )

    # Deals where this user is the buyer
    buyer_deals = relationship(
        "Deal",
        back_populates="buyer",
        foreign_keys="[Deal.buyer_id]",
        cascade="all, delete-orphan"
    )

    # Deals where this user is the supplier
    supplier_deals = relationship(
        "Deal",
        back_populates="supplier",
        foreign_keys="[Deal.supplier_id]",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<User(id={self.id!r}, name={self.name!r}, "
            f"email={self.email!r}, role={self.role!r})>"
        )

