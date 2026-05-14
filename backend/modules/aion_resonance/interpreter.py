from backend.modules.aion_resonance import reply_mapper

def parse_message(msg: str):
    """Very simple L0 interpreter to decide how to respond."""
    msg_l = msg.lower()
    if "yes" in msg_l or "true" in msg_l:
        intent = "affirmative"
    elif "no" in msg_l or "false" in msg_l:
        intent = "negative"
    elif "?" in msg_l:
        intent = "question"
    else:
        intent = "ack"
    return reply_mapper.generate_phi(intent)