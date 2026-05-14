from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, select
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from backend.database import Base
from .user import User  # ensure User is importable for expression

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"extend_existing": True}

    # ─── Columns ───────────────────────────────────────────────────────────────
    id             = Column(Integer, primary_key=True, index=True)
    title          = Column(String,  nullable=False, unique=True, index=True)
    description    = Column(String,  nullable=True)
    price_per_kg   = Column(Float,   nullable=False, default=0.0)
    image_url      = Column(String,  nullable=True)
    origin_country = Column(String,  nullable=True)
    category       = Column(String,  nullable=True)
    created_at     = Column(DateTime, nullable=False, default=datetime.utcnow)

    # ─── Foreign key & relationship to User ────────────────────────────────────
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    owner    = relationship(
        "User",
        back_populates="products_owned",     # <-- make sure your User model has `products_owned`
        passive_deletes=True
    )

    # ─── Relationships to Deal & Shipment ───────────────────────────────────────
    deals     = relationship(
        "Deal",
        back_populates="product",            # <-- matches Deal.product
        cascade="all, delete-orphan",
    )
    shipments = relationship(
        "Shipment",
        back_populates="product",            # <-- matches Shipment.product
        cascade="all, delete-orphan",
    )

    # ─── Hybrid property for owner's email ─────────────────────────────────────
    @hybrid_property
    def owner_email(self):
        # return the related User.email when accessing on ORM instances
        return self.owner.email

    @owner_email.expression
    def owner_email(cls):
        # produces a correlated subquery for filtering by email
        return (
            select(User.email)
            .where(User.id == cls.owner_id)
            .scalar_subquery()
        )

    def __repr__(self):
        return (
            f"<Product(id={self.id!r}, title={self.title!r}, "
            f"price_per_kg={self.price_per_kg!r}, owner_email={self.owner_email!r})>"
        )