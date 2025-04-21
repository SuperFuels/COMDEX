from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes import auth, product, deal, admin
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# ✅ Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("comdex")

# ✅ Initialize FastAPI app
app = FastAPI(
    title="COMDEX API",
    version="1.0.0",
    description="Global Commodity Marketplace API"
)

# ✅ Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Mount static files (e.g. product images)
app.mount("/uploaded_images", StaticFiles(directory="uploaded_images"), name="uploaded_images")

# ✅ Register route modules
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(product.router, prefix="/products", tags=["Products"])
app.include_router(deal.router)      # Deals router handles its own prefixes
app.include_router(admin.router)     # Admin router handles its own prefixes

# ✅ Root route
@app.get("/")
def read_root() -> dict:
    return {"message": "🚀 Welcome to the COMDEX API!"}

# ✅ Health check route
@app.get("/health")
def health_check() -> dict:
    try:
        engine = create_engine("postgresql://comdex:Wn8smx123@localhost/comdex")
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful.")
        return {"status": "ok", "database": "connected"}
    except OperationalError:
        logger.error("❌ Database connection failed.", exc_info=True)
        return {"status": "error", "database": "not connected"}

