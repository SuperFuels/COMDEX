# backend/modules/glyphvault/vault_logger.py

import logging

# Configure a dedicated logger for vault audit
vault_logger = logging.getLogger("glyphvault.audit")
vault_logger.setLevel(logging.INFO)

if not vault_logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    vault_logger.addHandler(handler)

def log_event(event_type: str, details: dict):
    """
    Log a vault audit event with event type and details.

    Args:
        event_type (str): The type of event (e.g., "SAVE", "RESTORE", "DELETE", "ACCESS_DENIED")
        details (dict): Additional metadata about the event
    """
    message = f"VaultEvent: {event_type} | Details: {details}"
    vault_logger.info(message)