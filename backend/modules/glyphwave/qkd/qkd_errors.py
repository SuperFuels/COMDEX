# backend/modules/glyphwave/qkd/qkd_errors.py

class QKDPolicyViolationError(Exception):
    """
    Raised when QKD enforcement fails during symbolic execution -
    e.g., missing GKey, tampering detected, or QKD required but not established.
    """
    def __init__(self, message="QKD policy violation during symbolic execution."):
        super().__init__(message)