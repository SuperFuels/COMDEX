"""
Photon Semantics
----------------
Defines the interpretation (meaning) of Photon expressions
beyond syntactic rewriting. Placeholder for Phase 2.
"""

class PhotonSemantics:
    def eval(self, expr, env=None):
        """
        Evaluate a Photon expression under a given environment.
        env: dict mapping symbols → values.
        """
        raise NotImplementedError("Semantic evaluation not yet implemented.")

# Singleton instance
semantics = PhotonSemantics()