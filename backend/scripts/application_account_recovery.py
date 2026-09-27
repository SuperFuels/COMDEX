#!/usr/bin/env python3
"""Operator command for off-device Tessaris application-account recovery."""

from __future__ import annotations

import argparse
from getpass import getpass
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.modules.aion_business.runtime.application_account_recovery import (
    ApplicationAccountRecoveryStore,
)


def _write_public_descriptor(path: Path, descriptor: dict) -> None:
    target = path.expanduser().resolve()
    if target.exists():
        raise ValueError("public_descriptor_destination_exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(descriptor, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    target.chmod(0o644)


def _password(*, confirm: bool) -> str:
    value = getpass("Recovery-kit password: ")
    if confirm and value != getpass("Confirm recovery-kit password: "):
        raise ValueError("recovery_password_confirmation_mismatch")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create or use an off-device Tessaris account-root recovery kit. "
            "Passwords are read interactively and never accepted as arguments."
        )
    )
    parser.add_argument("--root", type=Path, required=True, help="Local account-authority state directory")
    parser.add_argument(
        "--runtime-mode", choices=("development", "test", "production"), default="production",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    initialise = subparsers.add_parser("initialize")
    initialise.add_argument("--workspace", required=True)
    initialise.add_argument("--owner", required=True)
    initialise.add_argument("--device", required=True)
    initialise.add_argument("--kit", type=Path, required=True)
    initialise.add_argument("--public-descriptor", type=Path, required=True)
    initialise.add_argument(
        "--confirmation", required=True,
        help='Must equal "CREATE OFF-DEVICE ACCOUNT RECOVERY KIT"',
    )

    recover = subparsers.add_parser("recover")
    recover.add_argument("--kit", type=Path, required=True)
    recover.add_argument("--current-descriptor", type=Path, required=True)
    recover.add_argument("--expected-account", required=True)
    recover.add_argument("--device", required=True)
    recover.add_argument("--actor", required=True)
    recover.add_argument("--public-descriptor", type=Path, required=True)
    recover.add_argument(
        "--confirmation", required=True,
        help='Must equal "RECOVER ACCOUNT AND REVOKE PRIOR DEVICES"',
    )

    subparsers.add_parser("status")
    arguments = parser.parse_args()
    store = ApplicationAccountRecoveryStore(arguments.root, runtime_mode=arguments.runtime_mode)

    if arguments.command == "status":
        descriptor = store.descriptor()
        print(json.dumps({
            "account_id": descriptor["account_id"],
            "workspace_id": descriptor["workspace_id"],
            "recovery_epoch": descriptor["recovery_epoch"],
            "active_devices": descriptor["active_devices"],
            "descriptor_sha256": sha256(
                json.dumps(
                    descriptor,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
        }, indent=2, sort_keys=True))
        return 0

    if arguments.command == "initialize":
        result = store.initialize(
            workspace_id=arguments.workspace,
            owner_id=arguments.owner,
            device_id=arguments.device,
            password=_password(confirm=True),
            recovery_kit_path=arguments.kit,
            confirmation=arguments.confirmation,
        )
    else:
        current = json.loads(arguments.current_descriptor.expanduser().read_text(encoding="utf-8"))
        result = store.recover_clean_device(
            recovery_kit_path=arguments.kit,
            password=_password(confirm=False),
            current_descriptor=current,
            expected_account_id=arguments.expected_account,
            new_device_id=arguments.device,
            actor_id=arguments.actor,
            confirmation=arguments.confirmation,
        )
    _write_public_descriptor(arguments.public_descriptor, result["descriptor"])
    print(json.dumps({
        "account_id": result["account_id"],
        "workspace_id": result["workspace_id"],
        "recovery_epoch": result["recovery_epoch"],
        "descriptor_sha256": result["descriptor_sha256"],
        "public_descriptor": str(arguments.public_descriptor.expanduser().resolve()),
        "raw_private_key_exposed": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
