from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base  # Ensure Base is imported correctly

from models.deal import Deal  # Required for foreign_keys references

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)  # To store the hashed password
    role = Column(String, default="user")  # Default role is "user"

    # Relationship to link the user with the deals they are buyers in
    buyer_deals = relationship(
        "Deal",
        back_populates="buyer",
        foreign_keys="[Deal.buyer_id]",
        cascade="all, delete-orphan"
    )

    # Relationship to link the user with the deals they are suppliers in
    supplier_deals = relationship(
        "Deal",
        back_populates="supplier",
        foreign_keys="[Deal.supplier_id]",
        cascade="all, delete-orphan"
    )

    # Relationship to link the user with their products
    products = relationship(
        "Product",
        back_populates="owner",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, email={self.email}, role={self.role})>"

