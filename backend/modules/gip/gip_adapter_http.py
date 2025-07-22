# File: backend/modules/gip/gip_adapter_http.py

import requests
from .gip_packet import create_gip_packet

def send_gip_packet_http(destination_url: str, packet_type: str, channel: str, payload: dict) -> dict:
    """
    Send a GIP packet over HTTP POST.

    Args:
        destination_url (str): Target endpoint URL.
        packet_type (str): The symbolic packet type.
        channel (str): The logic or routing layer.
        payload (dict): Symbolic content.

    Returns:
        dict: Response from the remote server.
    """
    packet = create_gip_packet(packet_type, channel, payload)
    try:
        response = requests.post(destination_url, json=packet)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e), "packet": packet}

# Example usage:
# send_gip_packet_http("https://glyphnet-node.io/gip", "teleport", "luxnet", {"coords": [0,1,2]})
