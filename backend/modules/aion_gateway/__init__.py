"""
AION Agent Gateway v0.

Backend-only, dry-run-only intake layer for normalizing inbound human/agent
requests into canonical preview contracts.

This module must not expose public routes, execute workflows, mutate business
state, call providers, or create real FulfilmentJob records in v0.
"""

GATEWAY_PROTOCOL_VERSION = "aion.gateway.v0.1"
