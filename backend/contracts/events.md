# Event Contracts — Codex ↔ Photon ↔ QWave ↔ SQI ↔ Pattern Engine

This document defines the **canonical JSON contracts** for all events exchanged
across the system.  
All downstream code (schemas.py, beam_store, KG export, WebSockets) must conform exactly.  
If a change is needed, update this file **first**, then schemas.py.

---

## BeamEvent

Represents execution of a single operation (beam step).

```json
{
  "event_type": "BeamEvent",
  "eid": "uuid-v4",
  "origin": "photon|codex|qwave",
  "timestamp": "2025-09-26T12:00:00Z",
  "opcode": "∇|⊗|□|MOV|ADD",
  "args": ["R1", "R2", "5"],
  "precision": "fp4|fp8|int8|symbolic",
  "metadata": {
    "cost": 1.23,
    "sqi": 0.92,
    "drift": 0.03
  },
  "entanglements": ["eid-1234", "eid-5678"]
}