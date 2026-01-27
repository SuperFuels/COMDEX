#!/usr/bin/env python3
# pip install telethon

import os
import sys
import csv
import json
import time
import asyncio
import argparse
from pathlib import Path
from typing import Dict, Any, Set, Tuple, List, Optional

from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.types import User


def eprint(*args):
    print(*args, file=sys.stderr)


def norm_target(s: str) -> str:
    s = s.strip()
    if not s:
        return s
    # Accept:
    # - https://t.me/xxx
    # - t.me/xxx
    # - @xxx
    # - xxx
    if s.startswith("https://t.me/"):
        return s
    if s.startswith("t.me/"):
        return "https://" + s
    if s.startswith("@"):
        return s[1:]
    return s


def norm_username(u: Optional[str]) -> str:
    if not u:
        return ""
    u = u.strip()
    if not u:
        return ""
    if u.startswith("@"):
        return u
    return "@" + u


def load_targets(args) -> List[str]:
    targets: List[str] = []
    for t in args.group:
        t = norm_target(t)
        if t:
            targets.append(t)

    if args.groups_file:
        p = Path(args.groups_file)
        if not p.exists():
            raise SystemExit(f"groups file not found: {p}")
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            targets.append(norm_target(line))

    # de-dupe in order
    seen = set()
    uniq = []
    for t in targets:
        if t in seen:
            continue
        seen.add(t)
        uniq.append(t)
    return uniq


async def safe_iter_participants(client: TelegramClient, entity, aggressive: bool):
    async for u in client.iter_participants(entity, aggressive=aggressive):
        yield u


def load_seen_keys(raw_jsonl_path: Path) -> Set[Tuple[int, str]]:
    """
    Build a set of (user_id, group) keys already stored in raw jsonl,
    so repeated runs don't duplicate the audit log.
    """
    seen: Set[Tuple[int, str]] = set()
    if not raw_jsonl_path.exists():
        return seen

    with raw_jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                uid = int(r.get("user_id", 0))
                grp = str(r.get("group", "")).strip()
                if uid and grp:
                    seen.add((uid, grp))
            except Exception:
                continue
    return seen


async def fetch_group_users(
    client: TelegramClient,
    target: str,
    aggressive: bool,
    include_no_username: bool,
    sleep_ms: int,
    run_id: str,
) -> List[Dict[str, Any]]:
    """
    Returns list of dicts:
      {group, user_id, username, scraped_at, run_id}
    """
    out: List[Dict[str, Any]] = []
    group_entity = await client.get_entity(target)
    scraped_at = int(time.time())

    eprint(f"[+] Fetching participants for: {target}")

    n_seen = 0
    while True:
        try:
            async for u in safe_iter_participants(client, group_entity, aggressive=aggressive):
                n_seen += 1
                if not isinstance(u, User):
                    continue

                username = norm_username(getattr(u, "username", None))
                if (not username) and (not include_no_username):
                    # Skip users without public usernames unless requested
                    pass
                else:
                    out.append(
                        {
                            "group": target,
                            "user_id": int(u.id),
                            "username": username,
                            "scraped_at": scraped_at,
                            "run_id": run_id,
                        }
                    )

                if sleep_ms > 0:
                    await asyncio.sleep(sleep_ms / 1000.0)

            break

        except FloodWaitError as fe:
            wait_s = int(getattr(fe, "seconds", 0) or 0)
            eprint(f"[!] FloodWait: sleeping {wait_s}s")
            await asyncio.sleep(wait_s + 1)
            continue

        except RPCError as re:
            eprint(f"[!] RPCError on {target}: {re}. Retrying in 3s...")
            await asyncio.sleep(3)
            continue

    eprint(f"[+] Done {target}: rows={len(out)} (seen={n_seen})")
    return out


def append_raw_jsonl(raw_jsonl_path: Path, rows: List[Dict[str, Any]], seen_keys: Set[Tuple[int, str]]) -> int:
    raw_jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    new_count = 0
    with raw_jsonl_path.open("a", encoding="utf-8") as f:
        for r in rows:
            uid = int(r["user_id"])
            grp = str(r["group"]).strip()
            k = (uid, grp)
            if k in seen_keys:
                continue
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            seen_keys.add(k)
            new_count += 1
    return new_count


def rebuild_outputs_from_raw(raw_jsonl_path: Path, out_dir: Path) -> None:
    """
    Rebuild users.txt (unique usernames) and users.csv (deduped by user_id+group)
    from the accumulated raw.jsonl.
    """
    if not raw_jsonl_path.exists():
        raise SystemExit(f"raw jsonl not found: {raw_jsonl_path}")

    # dedupe by (user_id, group) for CSV
    dedup: Dict[Tuple[int, str], Dict[str, Any]] = {}

    # unique usernames for txt
    usernames: Set[str] = set()

    with raw_jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue

            uid = int(r.get("user_id", 0) or 0)
            grp = str(r.get("group", "")).strip()
            uname = norm_username(r.get("username", ""))

            if uname:
                usernames.add(uname)

            if uid and grp:
                key = (uid, grp)
                # keep the latest record by scraped_at (if present)
                prev = dedup.get(key)
                if not prev:
                    dedup[key] = {
                        "group": grp,
                        "user_id": uid,
                        "username": uname,
                        "scraped_at": int(r.get("scraped_at", 0) or 0),
                        "run_id": str(r.get("run_id", "") or ""),
                    }
                else:
                    t_prev = int(prev.get("scraped_at", 0) or 0)
                    t_new = int(r.get("scraped_at", 0) or 0)
                    if t_new >= t_prev:
                        prev["username"] = uname
                        prev["scraped_at"] = t_new
                        prev["run_id"] = str(r.get("run_id", "") or "")

    out_dir.mkdir(parents=True, exist_ok=True)

    # users.txt
    txt_path = out_dir / "users.txt"
    txt_path.write_text(
        "\n".join(sorted(usernames, key=lambda x: x.lower())) + ("\n" if usernames else ""),
        encoding="utf-8",
    )

    # users.csv
    csv_path = out_dir / "users.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["group", "user_id", "username", "scraped_at", "run_id"])
        w.writeheader()
        # stable-ish order: group then user_id
        for key in sorted(dedup.keys(), key=lambda k: (k[1].lower(), k[0])):
            w.writerow(dedup[key])

    eprint(f"[✓] Rebuilt:\n  {txt_path}\n  {csv_path}\n  {raw_jsonl_path}")


async def run():
    p = argparse.ArgumentParser()
    p.add_argument("--group", action="append", default=[], help="Group link/username. Repeatable.")
    p.add_argument("--groups-file", default="", help="Text file with one group per line.")
    p.add_argument("--out-dir", default="data/telegram", help="Output dir (repo-relative ok).")
    p.add_argument("--aggressive", action="store_true", help="Try harder to enumerate (may hit limits).")
    p.add_argument("--include-no-username", action="store_true", help="Include users without usernames.")
    p.add_argument("--sleep-ms", type=int, default=0, help="Sleep between users (avoid rate limits).")
    p.add_argument("--reset", action="store_true", help="Wipe raw/users outputs before scraping.")

    args = p.parse_args()

    api_id = os.getenv("TG_API_ID", "").strip()
    api_hash = os.getenv("TG_API_HASH", "").strip()
    session = os.getenv("TG_SESSION", "session")

    if not api_id or not api_hash:
        raise SystemExit("Set TG_API_ID and TG_API_HASH env vars (from my.telegram.org).")

    targets = load_targets(args)
    if not targets:
        raise SystemExit("Provide --group ... and/or --groups-file ...")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_jsonl_path = out_dir / "users.raw.jsonl"
    if args.reset:
        for pth in [raw_jsonl_path, out_dir / "users.txt", out_dir / "users.csv"]:
            if pth.exists():
                pth.unlink()
        eprint("[!] Reset outputs (deleted users.raw.jsonl/users.txt/users.csv)")

    seen_keys = load_seen_keys(raw_jsonl_path)

    run_id = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    eprint(f"[i] run_id={run_id} targets={len(targets)} out_dir={out_dir}")

    client = TelegramClient(session, int(api_id), api_hash)

    total_new = 0
    async with client:
        for t in targets:
            rows = await fetch_group_users(
                client,
                t,
                aggressive=args.aggressive,
                include_no_username=args.include_no_username,
                sleep_ms=args.sleep_ms,
                run_id=run_id,
            )
            new_count = append_raw_jsonl(raw_jsonl_path, rows, seen_keys)
            total_new += new_count
            eprint(f"[+] {t}: appended {new_count} new rows")

    rebuild_outputs_from_raw(raw_jsonl_path, out_dir)
    eprint(f"[✓] Done. Appended total new rows: {total_new}")


if __name__ == "__main__":
    asyncio.run(run())