# models/product.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    origin_country = Column(String, nullable=False)
    price_per_kg = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    owner_email = Column(String, ForeignKey("users.email"), nullable=False)  # Linking to User by email

    # Relationship with User (one-to-many relationship)
    owner = relationship("User", back_populates="products")

    # Relationship to link the product with the deals
    deals = relationship("Deal", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product(id={self.id}, title={self.title}, price_per_kg={self.price_per_kg}, category={self.category})>"

