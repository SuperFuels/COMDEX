class TamperedPayloadError(Exception):
    """Raised when GWave payload decryption fails due to tampering or key mismatch."""
    def __init__(self, message="Tampered or invalid QKD-encrypted payload."):
        super().__init__(message)