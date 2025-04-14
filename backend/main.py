from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, product, deal

app = FastAPI()

# Allow CORS for frontend on localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # ✅ adjust if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(product.router, prefix="/products", tags=["Products"])
app.include_router(deal.router, prefix="/deals", tags=["Deals"])

# Base route
@app.get("/")
def read_root():
    return {"message": "Welcome to COMDEX API"}

