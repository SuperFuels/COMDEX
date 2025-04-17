from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, product, deal, admin  # Added admin route import
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# ✅ Allow CORS for frontend on localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow the frontend dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Include API routes with clean prefixes
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(product.router, prefix="/products", tags=["Products"])
app.include_router(deal.router, prefix="/deals", tags=["Deals"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

# ✅ Root health check
@app.get("/")
def read_root():
    return {"message": "Welcome to COMDEX API"}

# ✅ Health check with DB connectivity verification
@app.get("/health")
def health_check():
    try:
        # Replace with your actual database credentials
        engine = create_engine("postgresql://comdex:Wn8smx123@localhost/comdex")
        with engine.connect() as connection:
            # Using text() for SQL query execution
            connection.execute(text("SELECT 1"))  # Simple query to check DB connection
        return {"status": "ok", "database": "connected"}
    except OperationalError:
        logger.error("Database connection failed")
        return {"status": "error", "database": "not connected"}

