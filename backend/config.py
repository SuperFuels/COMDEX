import os
from dotenv import load_dotenv

# load env.yaml/.env
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME")

# if you have a SQLALCHEMY_DATABASE_URL override, use it; otherwise build from Cloud SQL unix socket
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL") or (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}"
    f"?host=/cloudsql/{INSTANCE_CONNECTION_NAME}"
)
