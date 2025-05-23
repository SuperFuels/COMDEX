from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Product(Base):
    __tablename__ = "products"

    id             = Column(Integer, primary_key=True, index=True)
    title          = Column(String, nullable=False)
    origin_country = Column(String, nullable=False)
    category       = Column(String, nullable=False)
    description    = Column(String, nullable=False)
    image_url      = Column(String, nullable=False)
    price_per_kg   = Column(Float, nullable=False)
    owner_email    = Column(String, ForeignKey("users.email"), nullable=False)

    # ─── NEW FIELDS ──────────────────────────
    change_pct     = Column(Float, nullable=False, default=0.0)
    rating         = Column(Float, nullable=False, default=0.0)

    # relationships
    owner = relationship("User", back_populates="products")
    deals = relationship(
        "Deal",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<Product("
            f"id={self.id!r}, title={self.title!r}, origin_country={self.origin_country!r}, "
            f"category={self.category!r}, price_per_kg={self.price_per_kg!r}, "
            f"owner_email={self.owner_email!r}, change_pct={self.change_pct!r}, "
            f"rating={self.rating!r}"
            f")>"
        )

