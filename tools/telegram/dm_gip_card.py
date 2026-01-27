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
)

# -------- config via env --------
API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
SESSION = os.getenv("TG_SESSION", "data/telegram/gip0101")  # prefix; telethon creates .session

IN_FILE = Path(os.getenv("TG_DM_IN", "data/telegram/usernames.txt"))   # one username per line
OUT_LOG = Path(os.getenv("TG_DM_LOG", "data/telegram/dm_log.json"))

MAX_SEND = int(os.getenv("TG_DM_MAX", "5"))                 # send to 5 total per run
SLEEP_BETWEEN_SEC = float(os.getenv("TG_DM_SLEEP", "12"))   # pause between DMs

# Media (your GIF in repo)
GIF_PATH = os.getenv(
    "TG_DM_GIF",
    "/workspaces/COMDEX/frontend/public/images/GIP_repo_animated.gif"
)

# Links (optional follow-up msg so caption stays clean)
GROUP_LINK = os.getenv("TG_GROUP_LINK", "https://t.me/ElonDeSade")
BOT_START_LINK = os.getenv("TG_BOT_START", "https://t.me/YourBotUsername?start=gip_guard")
X_LINK = os.getenv("TG_X_LINK", "https://x.com/Glyph_Os")
SITE_LINK = os.getenv("TG_SITE_LINK", "https://tessaris.ai")

SEND_LINKS_FOLLOWUP = os.getenv("TG_DM_SEND_LINKS", "1").strip() not in ("0", "false", "False")

CAPTION = os.getenv(
    "TG_DM_CAPTION",
    """Most tokens launch memes.
$GIP is launching the next internet layer — on Solana.

GlyphOS Alpha — live right now
• 61× meaning compression (depth 60 locked proof)
• WirePack deltas — 54%+ savings vs gzip JSON
• AION organism — self-healing, self aware intelligence
• SQI runtime — quantum-like reasoning on your laptop

Demos already running → tessaris.ai

Fair Launch Countdown
GIP Fair Launch goes live Tomorrow at 9:00 PM UK (GMT) • Wed, 28 Jan 2026 21:00:00 UTC
⏳ 1d 10h 14m 48s remaining

Do this in 20 seconds:
🥱 Join the GIP Telegram group
🤘 Scroll pinned proofs & live demos
😎 Start the Guard bot (launch + liquidity alerts)

$GIP isn’t waiting. Are you? 💪

👇 Enter before it’s obvious 👇

✉ Guard Bot | 🐣 X | 🌐 tessaris.ai | 📢 Telegram Group"""
).strip()

LINKS_TEXT = os.getenv(
    "TG_DM_LINKS_TEXT",
    (
        "Links:\n"
        f"• 📢 Telegram Group: {GROUP_LINK}\n"
        f"• ✉ Guard Bot: {BOT_START_LINK}\n"
        f"• 🐣 X: {X_LINK}\n"
        f"• 🌐 Site: {SITE_LINK}\n\n"
        "If you don’t want DMs, reply ‘stop’ and I won’t message again."
    )
).strip()

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
    return out

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

async def main():
    if not API_ID or not API_HASH:
        raise SystemExit("Set TG_API_ID and TG_API_HASH in env")
    gif = Path(GIF_PATH)
    if not gif.exists():
        raise SystemExit(f"GIF not found: {gif}")

    usernames = load_usernames(IN_FILE)
    log = load_log(OUT_LOG)

    already_sent = set(log.get("sent", {}).keys())
    already_failed = set(log.get("failed", {}).keys())

    candidates = [u for u in usernames if u not in already_sent and u not in already_failed]
    to_send = candidates[:MAX_SEND]

    print(f"Loaded {len(usernames)} usernames.")
    print(f"Already sent: {len(already_sent)} | failed: {len(already_failed)}")
    print(f"Will attempt: {len(to_send)} (max {MAX_SEND})\n")

    if not to_send:
        print("Nothing to send.")
        return

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.start()  # will prompt phone on first run

    ok = 0
    fail = 0

    for i, uname in enumerate(to_send, 1):
        target = f"@{uname}"
        try:
            entity = await client.get_entity(target)

            # 1) Send GIF + caption (inline)
            await client.send_file(
                entity,
                file=str(gif),
                caption=CAPTION,
                force_document=False,  # IMPORTANT: inline
            )

            # 2) Optional follow-up links message
            if SEND_LINKS_FOLLOWUP:
                await client.send_message(entity, LINKS_TEXT, link_preview=True)

            ok += 1
            log.setdefault("sent", {})[uname] = {
                "at": int(time.time()),
                "target": target,
                "mode": "gif+caption" + ("+links" if SEND_LINKS_FOLLOWUP else ""),
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
            await asyncio.sleep(SLEEP_BETWEEN_SEC)

    print(f"\nDone. ok={ok} fail={fail} attempted={len(to_send)}")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())