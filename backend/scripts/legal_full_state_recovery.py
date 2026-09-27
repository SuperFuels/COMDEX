#!/usr/bin/env python3
"""Local operator command for encrypted Legal/GlyphChain device recovery."""

from __future__ import annotations

import argparse
from getpass import getpass
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from backend.modules.aion_business.runtime.legal_full_state_backup import LegalFullStateBackupService


def _password(*, confirm: bool) -> str:
    first = getpass("Recovery password: ")
    if confirm and first != getpass("Confirm recovery password: "):
        raise SystemExit("Recovery passwords do not match")
    return first


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create, inspect or restore a password-encrypted Tessaris Legal/GlyphChain device backup.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    export = sub.add_parser("export", help="Create a new encrypted full-state backup")
    export.add_argument("output", type=Path)
    export.add_argument("--workspace", required=True)
    export.add_argument("--actor", required=True)
    export.add_argument("--confirm-export", action="store_true", required=True)

    inspect = sub.add_parser("inspect", help="Authenticate and inspect a backup without restoring it")
    inspect.add_argument("backup", type=Path)

    restore = sub.add_parser("restore", help="Restore a backup into the configured clean device roots")
    restore.add_argument("backup", type=Path)
    restore.add_argument("--actor", required=True)
    restore.add_argument("--confirm-restore", action="store_true", required=True)
    restore.add_argument("--replace-existing", action="store_true")

    args = parser.parse_args()
    service = LegalFullStateBackupService()
    if args.command == "export":
        result = service.create_backup(
            args.output,
            password=_password(confirm=True),
            workspace_id=args.workspace,
            actor_id=args.actor,
            confirmation="EXPORT COMPLETE LEGAL AND GLYPHCHAIN STATE",
        )
    elif args.command == "inspect":
        result = service.inspect_backup(args.backup, password=_password(confirm=False))
    else:
        result = service.restore_backup(
            args.backup,
            password=_password(confirm=False),
            actor_id=args.actor,
            confirmation="RESTORE COMPLETE LEGAL AND GLYPHCHAIN STATE",
            acknowledge_replace_existing=bool(args.replace_existing),
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
