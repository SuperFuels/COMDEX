from pydantic import BaseModel

class ProductCreate(BaseModel):
    title: str
    origin_country: str
    price_per_kg: float
    category: str
    description: str
    image_url: str

class ProductUpdate(BaseModel):
    title: str
    origin_country: str
    price_per_kg: float
    category: str
    description: str
    image_url: str

class ProductOut(ProductCreate):
    id: int

    class Config:
        from_attributes = True

