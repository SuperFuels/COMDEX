#!/usr/bin/env python3
# tools/telegram/dm_gip_card.py
# pip install telethon python-dotenv

import asyncio
import json
import os
import time
from pathlib import Path
from typing import List, Dict, Any

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    UserPrivacyRestrictedError,
    ChatWriteForbiddenError,
    UsernameNotOccupiedError,
    UsernameInvalidError,
    PeerIdInvalidError,
    RPCError,
)

# -------- config via env --------
API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
SESSION = os.getenv("TG_SESSION", "data/telegram/gip0101")  # prefix; telethon creates .session

IN_FILE = Path(os.getenv("TG_DM_IN", "data/telegram/users.txt"))  # one @username per line
OUT_LOG = Path(os.getenv("TG_DM_LOG", "data/telegram/dm_log.json"))

MAX_SEND = int(os.getenv("TG_DM_MAX", "5"))                 # send to N total per run
SLEEP_BETWEEN_SEC = float(os.getenv("TG_DM_SLEEP", "45"))   # pause between DMs (go higher when warm)
JITTER_SEC = float(os.getenv("TG_DM_JITTER", "8"))          # random-ish jitter (we'll use time-based)

# Links
GROUP_LINK = os.getenv("TG_GROUP_LINK", "https://t.me/Glyph_Os").strip()
X_LINK = os.getenv("TG_X_LINK", "https://x.com/Glyph_Os").strip()
SITE_LINK = os.getenv("TG_SITE_LINK", "https://tessaris.ai").strip()

# -------- MESSAGE (TEXT ONLY) --------
# Put URLs on their own lines for best linkification in Telegram.
MESSAGE_DEFAULT = f"""💲🧬🔤💎  $GIP  💎🔤🧬💲

$GIP ⚡ on Solana — launching the next internet layer (not another meme)

🚀 GlyphOS Alpha — LIVE
✅ 61× meaning compression (depth-60 locked proof)
✅ WirePack deltas — 54%+ savings vs gzip JSON
✅ AION organism — self-healing, self-aware intelligence
✅ SQI runtime — quantum-like reasoning on your laptop

🧪 Demos running now:
{SITE_LINK}

⏳ FAIR LAUNCH COUNTDOWN
🗓 Wed, 28 Jan 2026 • 21:00 UTC (9:00 PM UK GMT)

⚡ Do this in 20 seconds:
👉 Join the GIP Telegram group
👉 Scroll pinned proofs + live demos
👉 Enable alerts inside the group

$GIP isn’t waiting. Are you? 💪
👇 Enter before it’s obvious 👇

📢 Telegram Group:
{GROUP_LINK}

🐣 X:
{X_LINK}
""".strip()

MESSAGE = os.getenv("TG_DM_TEXT", MESSAGE_DEFAULT).strip()

# -------- helpers --------
def load_usernames(path: Path) -> List[str]:
    if not path.exists():
        raise SystemExit(f"Input file not found: {path}")
    out: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("@"):
            s = s[1:]
        if 5 <= len(s) <= 32:
            out.append(s)
    # de-dupe while preserving order
    seen = set()
    uniq: List[str] = []
    for u in out:
        if u in seen:
            continue
        seen.add(u)
        uniq.append(u)
    return uniq

def load_log(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"sent": {}, "failed": {}, "ts": int(time.time())}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"sent": {}, "failed": {}, "ts": int(time.time())}

def save_log(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

def sleepy(base_sec: float, jitter_sec: float) -> float:
    # deterministic-ish jitter (no random import): based on current ms
    ms = int(time.time() * 1000) % 1000
    j = (ms / 1000.0) * jitter_sec
    return max(0.0, base_sec + j)

async def main():
    if not API_ID or not API_HASH:
        raise SystemExit("Set TG_API_ID and TG_API_HASH in env")

    usernames = load_usernames(IN_FILE)
    log = load_log(OUT_LOG)

    already_sent = set((log.get("sent") or {}).keys())
    already_failed = set((log.get("failed") or {}).keys())

    # reruns continue down the list
    candidates = [u for u in usernames if u not in already_sent and u not in already_failed]
    to_send = candidates[:MAX_SEND]

    print(f"Loaded {len(usernames)} usernames from: {IN_FILE}")
    print(f"Already sent: {len(already_sent)} | failed: {len(already_failed)}")
    print(f"Will attempt: {len(to_send)} (max {MAX_SEND})\n")

    if not to_send:
        print("Nothing to send.")
        return

    print("\n----- MESSAGE TO SEND -----\n")
    print(MESSAGE)
    print("\n----- END MESSAGE -----\n")

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.start()

    ok = 0
    fail = 0

    for i, uname in enumerate(to_send, 1):
        target = f"@{uname}"
        try:
            entity = await client.get_entity(target)

            # TEXT ONLY (avoids SendMediaRequest -> PeerFloodError spikes)
            await client.send_message(
                entity,
                MESSAGE,
                link_preview=True,
                parse_mode=None,  # IMPORTANT: allow Telegram to auto-link plain URLs
            )

            ok += 1
            log.setdefault("sent", {})[uname] = {
                "at": int(time.time()),
                "target": target,
                "mode": "text",
            }
            print(f"[OK {i}/{len(to_send)}] {target}")

        except FloodWaitError as e:
            wait_s = int(getattr(e, "seconds", 60))
            print(f"[FLOOD] Need to wait {wait_s}s. Stopping now to stay safe.")
            log.setdefault("failed", {})[uname] = {
                "at": int(time.time()),
                "target": target,
                "err": f"FLOOD_WAIT_{wait_s}",
            }
            save_log(OUT_LOG, log)
            await client.disconnect()
            return

        except RPCError as e:
            # Includes PeerFloodError (Too many requests)
            fail += 1
            name = e.__class__.__name__
            print(f"[FAIL] {target} -> {name}({str(e)[:120]})")
            log.setdefault("failed", {})[uname] = {
                "at": int(time.time()),
                "target": target,
                "err": f"{name}:{str(e)[:200]}",
            }
            # If Telegram is flagging you (PeerFloodError), you should stop early
            if "PeerFlood" in name or "Too many requests" in str(e):
                save_log(OUT_LOG, log)
                await client.disconnect()
                print("\n[STOP] PeerFlood/Too many requests detected. Pause for hours+ and increase TG_DM_SLEEP.")
                return

        except (UserPrivacyRestrictedError, ChatWriteForbiddenError, PeerIdInvalidError) as e:
            fail += 1
            log.setdefault("failed", {})[uname] = {
                "at": int(time.time()),
                "target": target,
                "err": e.__class__.__name__,
            }
            print(f"[FAIL] {target} -> {e.__class__.__name__}")

        except (UsernameNotOccupiedError, UsernameInvalidError) as e:
            fail += 1
            log.setdefault("failed", {})[uname] = {
                "at": int(time.time()),
                "target": target,
                "err": e.__class__.__name__,
            }
            print(f"[FAIL] {target} -> {e.__class__.__name__}")

        except Exception as e:
            fail += 1
            log.setdefault("failed", {})[uname] = {
                "at": int(time.time()),
                "target": target,
                "err": repr(e)[:300],
            }
            print(f"[FAIL] {target} -> {repr(e)[:200]}")

        save_log(OUT_LOG, log)

        if i < len(to_send):
            t = sleepy(SLEEP_BETWEEN_SEC, JITTER_SEC)
            await asyncio.sleep(t)

    print(f"\nDone. ok={ok} fail={fail} attempted={len(to_send)}")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())