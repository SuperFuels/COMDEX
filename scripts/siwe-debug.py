import traceback
from siwe import SiweMessage

# paste one of your failing raw messages here:
RAW = """swift-area-459514-d1.web.app wants you to sign in with your Ethereum account:
0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC

Sign in to STICKEY

URI: https://swift-area-459514-d1.web.app
Version: 1
Chain ID: 1
Nonce: LhgaXQoBtHqyG8JRK6Zt2A
Issued At: 2025-05-27T10:47:22Z"""

try:
    # try both the old and new entrypoints:
    print("-> parse_message:")
    msg1 = SiweMessage.parse_message(RAW)
    print(msg1)
except Exception:
    traceback.print_exc()

try:
    print("-> constructor fallback:")
    msg2 = SiweMessage(RAW)
    print(msg2)
except Exception:
    traceback.print_exc()
