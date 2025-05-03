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
    owner_email = Column(String, ForeignKey("users.email"), nullable=False)

    # one User can have many Products
    owner = relationship("User", back_populates="products")

    # one Product can have many Deals
    deals = relationship(
        "Deal",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<Product("
            f"id={self.id!r}, title={self.title!r}, price_per_kg={self.price_per_kg!r}, "
            f"owner_email={self.owner_email!r}"
            ")>"
        )

