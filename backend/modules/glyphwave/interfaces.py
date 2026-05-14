"""
Interfaces / Protocols for GlyphWave.
Defines modular, swappable components for carrier orchestration.
"""

from typing import Protocol, Dict, Any, Optional, Iterable


class IGlyphWaveCarrier(Protocol):
    """
    Interface for GlyphWave transmission carriers.
    Responsible for emitting and capturing .gwip packets.
    """

    def emit(self, gwip: Dict[str, Any]) -> None:
        """Transmit a GWIP packet into the carrier."""
        ...

    def capture(self) -> Optional[Dict[str, Any]]:
        """Attempt to receive a GWIP packet from the carrier."""
        ...

    def stats(self) -> Dict[str, Any]:
        """Return live metrics: SNR, dropped packets, queue size, etc."""
        ...

    def close(self) -> None:
        """Gracefully shut down the carrier."""
        ...

    def flush(self) -> None:
        """Optional: clear any buffered packets."""
        ...


class IPhaseScheduler(Protocol):
    """
    Interface for phase-based beam scheduling and alignment.
    Typically implemented using PLL + jitter + drift compensation.
    """

    def schedule(self, gwip: Dict[str, Any]) -> Dict[str, Any]:
        """Apply timing policies and annotate the GWIP packet."""
        ...

    def set_policy(self, policy: Dict[str, Any]) -> None:
        """Update internal scheduling policy."""
        ...

    def metrics(self) -> Dict[str, Any]:
        """Return internal scheduler metrics."""
        ...


class IGWIPCodec(Protocol):
    """
    Interface for encoding/decoding .gip ⇄ .gwip packets.
    Translates between generic symbolic packets and modulated beam form.
    """

    def encode(self, gip: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a GIP packet to GWIP format."""
        ...

    def decode(self, gwip: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a GWIP packet back into GIP format."""
        ...

    def upgrade(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """Apply advanced modulation/envelope for quantum-grade beam injection."""
        ...

    def downgrade(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify a packet for legacy/low-fidelity transmission."""
        ...