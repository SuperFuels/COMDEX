from datetime import datetime

def get_current_timestamp() -> str:
    """Returns the current UTC timestamp in ISO 8601 format."""
    return datetime.utcnow().isoformat()