# backend/start.py

import os
from dotenv import load_dotenv
import uvicorn

# Load environment variables from .env (for local development)
load_dotenv()

if __name__ == "__main__":
    # Cloud Run injects PORT; default to 8080 for local dev
    port = int(os.environ.get("PORT", 8080))

    # Run the FastAPI app in main.py as "main:app"
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,      # hot-reload during local development
        log_level="info"
    )
