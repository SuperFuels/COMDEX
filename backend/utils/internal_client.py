from fastapi.testclient import TestClient

def get_client():
    from backend.main import app  # ✅ delayed import
    return TestClient(app)