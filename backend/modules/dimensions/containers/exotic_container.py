# ──────────────────────────────────────────────
#  Tessaris * Exotic Container (Stage 15)
#  AST Compression + Wave Signature Encoding
#  Black-hole-style symbolic storage (reversible)
# ──────────────────────────────────────────────

import os, json, zlib, base64, uuid, hashlib, logging
from typing import Any, Dict, Optional
from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer

logger = logging.getLogger(__name__)


class ExoticContainer(UCSBaseContainer):
    """
    ⚫ ExoticContainer
    Inherits UCSBaseContainer and provides:
        * AST / logic-tree compression
        * ψ-κ-T signature generation
        * entropy-sink (black-hole) simulation
        * reversible decompression / recall
    """

    def __init__(
        self,
        container_id: Optional[str] = None,
        runtime: Optional[Any] = None,
        geometry: str = "Exotic Compression Core",
        entropy_mode: str = "sink",
        compression_level: str = "stellar-core",
    ):
        self.container_id = container_id or str(uuid.uuid4())
        self.id = self.container_id
        name = f"EXO-{self.container_id}"

        super().__init__(
            name=name,
            geometry=geometry,
            runtime=runtime,
            container_type="exotic_container",
        )

        self.entropy_mode = entropy_mode
        self.compression_level = compression_level
        self.compressed_payload: Optional[str] = None
        self.wave_signature: Optional[Dict[str, float]] = None
        logger.info(f"[ExoticContainer] Initialized {name} ({geometry})")

    # ──────────────────────────────────────────────
    #  Compression / Decompression
    # ──────────────────────────────────────────────
    def compress_ast(self, logic_tree: Dict[str, Any]) -> str:
        """Compress a logic tree or AST to base64 string."""
        raw = json.dumps(logic_tree, sort_keys=True).encode()
        packed = zlib.compress(raw, level=9)
        encoded = base64.b64encode(packed).decode()
        self.compressed_payload = encoded
        self.wave_signature = self._generate_wave_signature(logic_tree)
        logger.debug(f"[ExoticContainer] Compressed AST: {len(raw)}->{len(encoded)} bytes.")
        return encoded

    def decompress_ast(self) -> Optional[Dict[str, Any]]:
        """Decompress previously stored AST."""
        if not self.compressed_payload:
            return None
        try:
            decoded = base64.b64decode(self.compressed_payload)
            raw = zlib.decompress(decoded)
            return json.loads(raw)
        except Exception as e:
            logger.error(f"[ExoticContainer] Decompression failed: {e}")
            return None

    # ──────────────────────────────────────────────
    #  Wave Signature Generation
    # ──────────────────────────────────────────────
    def _generate_wave_signature(self, data: Dict[str, Any]) -> Dict[str, float]:
        entropy = len(json.dumps(data)) % 97 / 97
        curvature = hashlib.md5(json.dumps(data).encode()).digest()[0] / 255
        T = (entropy + curvature) / 2
        return {"ψ": entropy, "κ": curvature, "T": T}

    # ──────────────────────────────────────────────
    #  Entropy Sink Simulation
    # ──────────────────────────────────────────────
    def collapse(self):
        """Simulate total compression / entropy sink."""
        self.visualize_state("collapsing")
        if self.entropy_mode == "sink":
            self.compressed_payload = None
        logger.info(f"[ExoticContainer] Collapsed (entropy sink mode).")

    # ──────────────────────────────────────────────
    #  Metadata / Export
    # ──────────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "entropy_mode": self.entropy_mode,
            "compression_level": self.compression_level,
            "signature": self.wave_signature,
            "compressed": bool(self.compressed_payload),
        })
        return base