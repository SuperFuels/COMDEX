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
)

# -------- config via env --------
API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
SESSION = os.getenv("TG_SESSION", "data/telegram/gip0101")  # prefix; telethon creates .session

IN_FILE = Path(os.getenv("TG_DM_IN", "data/telegram/users.txt"))  # one @username per line
OUT_LOG = Path(os.getenv("TG_DM_LOG", "data/telegram/dm_log.json"))

MAX_SEND = int(os.getenv("TG_DM_MAX", "10"))  # send to N total per run
SLEEP_BETWEEN_SEC = float(os.getenv("TG_DM_SLEEP", "12"))  # pause between DMs

# Media (your GIF in repo)
GIF_PATH = os.getenv(
    "TG_DM_GIF",
    "/workspaces/COMDEX/frontend/public/images/GIP_repo_animated.gif",
)

# Links
GROUP_LINK = os.getenv("TG_GROUP_LINK", "https://t.me/Glyph_Os").strip()
BOT_START_LINK = os.getenv("TG_BOT_START", "").strip()  # optional; can be empty
X_LINK = os.getenv("TG_X_LINK", "https://x.com/Glyph_Os").strip()
SITE_LINK = os.getenv("TG_SITE_LINK", "https://tessaris.ai").strip()

# IMPORTANT: default to ONE MESSAGE (no follow-up)
SEND_LINKS_FOLLOWUP = os.getenv("TG_DM_SEND_LINKS", "0").strip() not in ("0", "false", "False")

# -------- HYPE CARD (caption) --------
# Key: captions on media often fail to auto-link when you use markdown parse_mode.
# We explicitly send parse_mode=None and put URLs on their own lines for reliable linkification.
CAPTION_DEFAULT = f"""💲🧬🔤💎  $GIP  💎🔤🧬💲

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

CAPTION = os.getenv("TG_DM_CAPTION", CAPTION_DEFAULT).strip()

# Optional follow-up message (only sent when TG_DM_SEND_LINKS=1)
def build_links_text() -> str:
    lines = [
        "Links:",
        f"• 📢 Telegram Group: {GROUP_LINK}",
    ]
    if BOT_START_LINK:
        lines.append(f"• ✉ Bot: {BOT_START_LINK}")
    lines.extend(
        [
            f"• 🐣 X: {X_LINK}",
            f"• 🌐 Site: {SITE_LINK}",
            "",
            "If you don’t want DMs, reply ‘stop’ and I won’t message again.",
        ]
    )
    return "\n".join(lines).strip()


LINKS_TEXT = os.getenv("TG_DM_LINKS_TEXT", build_links_text()).strip()


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
        # basic sanity: telegram usernames are 5-32, letters/digits/underscore
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


async def main():
    if not API_ID or not API_HASH:
        raise SystemExit("Set TG_API_ID and TG_API_HASH in env")

    gif = Path(GIF_PATH)
    if not gif.exists():
        raise SystemExit(f"GIF not found: {gif}")

    usernames = load_usernames(IN_FILE)
    log = load_log(OUT_LOG)

    already_sent = set((log.get("sent") or {}).keys())
    already_failed = set((log.get("failed") or {}).keys())

    # IMPORTANT: reruns continue down the list (won't re-DM the same first N)
    candidates = [u for u in usernames if u not in already_sent and u not in already_failed]
    to_send = candidates[:MAX_SEND]

    print(f"Loaded {len(usernames)} usernames from: {IN_FILE}")
    print(f"Already sent: {len(already_sent)} | failed: {len(already_failed)}")
    print(f"Will attempt: {len(to_send)} (max {MAX_SEND})\n")

    if not to_send:
        print("Nothing to send.")
        return

    # Print the exact caption being sent (prevents “wrong caption” confusion)
    print("\n----- CAPTION TO SEND -----\n")
    print(CAPTION)
    print("\n----- END CAPTION -----\n")

    client = TelegramClient(SESSION, API_ID, API_HASH)
    await client.start()

    ok = 0
    fail = 0

    for i, uname in enumerate(to_send, 1):
        target = f"@{uname}"
        try:
            entity = await client.get_entity(target)

            # 1) Send GIF + caption (inline) — ONE message
            await client.send_file(
                entity,
                file=str(gif),
                caption=CAPTION,         # keep plain text urls
                force_document=False,    # inline media
                parse_mode=None,         # IMPORTANT: let Telegram auto-link
            )

            # 2) Optional follow-up links (OFF by default)
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