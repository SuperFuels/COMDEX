import os

# Cloud Run mounts your Cloud SQL socket under /cloudsql
DB_USER       = os.getenv("DB_USER", "")
DB_PASS       = os.getenv("DB_PASS", "")
DB_NAME       = os.getenv("DB_NAME", "")
DB_SOCKET     = os.getenv("DB_SOCKET_PATH", "")

# Fallback to a raw DATABASE_URL if you have one—but socket is preferred:
if DB_SOCKET:
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}"
        f"?host=/cloudsql/{DB_SOCKET}"
    )
else:
    SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

