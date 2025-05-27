# backend/routes/auth.py

import re
from fastapi import APIRouter, HTTPException, Request, Query
from datetime import datetime
import logging
from web3 import Web3

from ..utils.auth import generate_nonce
from siwe import SiweMessage

router = APIRouter(tags=["Auth"])
logger = logging.getLogger("routes.auth")
logging.basicConfig(level=logging.DEBUG)

# matches 0x + 40 hex chars, any case
HEX40 = re.compile(r"^0x[0-9a-fA-F]{40}$")


@router.get("/nonce")
def get_siwe_nonce(
    request: Request,
    address: str = Query(..., description="Wallet address")
):
    # 1) derive domain
    origin = request.headers.get("origin") or f"http://{request.client.host}:{request.url.port}"
    domain = origin.replace("https://", "").replace("http://", "")

    # 2) quick format check
    if not HEX40.match(address):
        raise HTTPException(status_code=400, detail="Invalid Ethereum address format")

    # 3) compute full EIP-55 checksum
    try:
        checksummed = Web3.to_checksum_address(address)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not checksum address")

    # 4) generate nonce + timestamp
    nonce     = generate_nonce()
    issued_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    # 5) build the SiweMessage
    siwe = SiweMessage(
        domain=domain,
        address=checksummed,
        statement="Sign in to STICKEY",
        uri=origin,
        version="1",
        chain_id=1,
        nonce=nonce,
        issued_at=issued_at,
    )
    msg = siwe.prepare_message()
    logger.debug("SIWE message: %r", msg)
    return {"message": msg}