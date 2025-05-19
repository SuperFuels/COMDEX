# backend/main.py

import os
import time
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# ensure uploads folder exists
os.makedirs("uploaded_images", exist_ok=True)

# load .env in non-prod
if os.getenv("ENV", "").lower() != "production":
    from dotenv import load_dotenv
    load_dotenv()

# give Cloud SQL socket & VPC connector time on cold start
time.sleep(3)

# import the single shared engine (configured in backend/database.py)
from database import engine

# set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("comdex")

# FastAPI app
app = FastAPI(
    title="COMDEX API",
    version="1.0.0",
    description="Global Commodity Marketplace API",
)

# configure CORS from env var (comma-separated list)
origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
allow_origins = [o.strip() for o in origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# serve user uploads
app.mount(
    "/uploaded_images",
    StaticFiles(directory="uploaded_images"),
    name="uploaded_images",
)

# import & include routers
from routes.auth      import router as auth_router
from routes.products  import router as products_router
from routes.deal      import router as deal_router
from routes.contracts import router as contracts_router
from routes.admin     import router as admin_router
from routes.user      import router as user_router

app.include_router(auth_router,      prefix="/auth",     tags=["Auth"])
app.include_router(products_router,  prefix="/products", tags=["Products"])
app.include_router(deal_router,      prefix="/deals",    tags=["Deals"])
app.include_router(contracts_router, prefix="/contracts",tags=["Contracts"])
app.include_router(admin_router,     prefix="/admin",    tags=["Admin"])
app.include_router(user_router,      prefix="/users",    tags=["Users"])

# root endpoint
@app.get("/", tags=["Root"])
def read_root():
    return {"message": "🚀 Welcome to the COMDEX API!"}

# health check
@app.get("/health", tags=["Health"])
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful.")
        return {"status": "ok", "database": "connected"}
    except OperationalError:
        logger.error("❌ Database connection failed.", exc_info=True)
        return {"status": "error", "database": "not connected"}

