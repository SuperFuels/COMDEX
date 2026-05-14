import uuid

def generate_uuid() -> str:
    """Generates a unique UUID string."""
    return str(uuid.uuid4())