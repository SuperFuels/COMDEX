from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, product, deal

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000"
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(product.router, prefix="/products", tags=["Products"])
app.include_router(deal.router, prefix="/deals", tags=["Deals"])

@app.get("/")
def read_root():
    return {"message": "Welcome to COMDEX API"}

