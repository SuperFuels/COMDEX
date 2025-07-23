# File: backend/modules/gip/gip_packet_schema.py

from jsonschema import validate, ValidationError

GIP_PACKET_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "glyphs": {
            "type": "array",
            "items": {"type": "object"}
        },
        "meta": {"type": "object"},
        "symbol": {"type": "string"},
        "command": {"type": "string"},
    },
    "required": ["type"],
    "additionalProperties": True
}

def validate_gip_packet(packet: dict):
    try:
        validate(instance=packet, schema=GIP_PACKET_SCHEMA)
    except ValidationError as e:
        raise ValueError(f"Invalid GIP packet: {e.message}")