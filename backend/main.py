from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, product, deal, admin
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="COMDEX API", version="1.0.0")

# ✅ CORS configuration to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Register route groups without redundant nesting
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(product.router, prefix="/products", tags=["Products"])
app.include_router(deal.router, prefix="/deals", tags=["Deals"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

# ✅ Root route
@app.get("/")
def read_root():
    return {"message": "Welcome to COMDEX API"}

# ✅ Health check route to test DB connectivity
@app.get("/health")
def health_check():
    try:
        engine = create_engine("postgresql://comdex:Wn8smx123@localhost/comdex")
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except OperationalError:
        logger.error("Database connection failed.")
        return {"status": "error", "database": "not connected"}

