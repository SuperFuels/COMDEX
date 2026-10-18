# GlyphChain and Legal application-account recovery

Status: local protocol, standalone monotonic registry service and AION desktop
session enforcement implemented; independently operated deployment, remaining
session issuers and live recovery validation remain release gates.

## Purpose

Application-account recovery is intentionally separate from whole-device,
Legal-key and GlyphChain network-identity backups. Restoring files from a lost
machine does not prove that the restorer owns the Tessaris account.

The implemented protocol creates two separate artefacts:

1. an encrypted account-root recovery kit which must be retained outside the
   Tessaris runtime; and
2. a root-signed public account descriptor which can be published or retained
   independently without exposing account secrets.

The stable account ID is derived from the Ed25519 account-root public key. The
kit contains the matching private root encrypted using scrypt
(`N=32768, r=8, p=1`) and AES-256-GCM. The password is never written into the
kit or runtime state. Production root-key custody uses the platform Keychain;
development tests use an owner-only file.

## Clean-device recovery

Recovery requires:

- the off-device encrypted kit;
- its password;
- the expected account ID;
- the current independently retained public descriptor;
- a new device ID; and
- the exact destructive-recovery confirmation.

Tessaris authenticates the kit, derives and verifies the root public key,
checks the expected account and workspace, verifies the current descriptor's
root signature, advances the recovery epoch and signs a replacement descriptor.
The new descriptor lists only the newly recovered device and declares every
unlisted device revoked. Its continuity field commits to the exact previous
descriptor digest.

Any consumer using the account authority can reject a stale session epoch and
any device omitted from the active descriptor. Wrong passwords, modified kits,
modified descriptors, unexpected account IDs, on-runtime kit destinations and
recovery into an already initialised target fail closed.

The installed desktop request signer and backend verifier use
`aion.flow.desktop-session.v2` whenever a descriptor is present. The signed
message includes the account ID and recovery epoch as well as the exact method,
target, body digest, device, person, workspace, timestamp and nonce. Legal,
GlyphChain administration and AION Flow requests therefore reject a session
from a pre-recovery epoch or a device absent from the active descriptor. A
client presenting account headers to a backend without the matching descriptor
also fails closed rather than falling back to the legacy session format.

`backend/scripts/application_account_recovery.py` provides interactive
`initialize`, `recover` and `status` commands. Recovery passwords are read from
the terminal and are never accepted as command-line arguments. Initialisation
and recovery can write a public descriptor suitable for independent
publication, while the encrypted kit remains owner-controlled.

## Freshness and publication boundary

The recovery kit cannot appoint its own latest account state. A person holding
an old valid descriptor can prove that it was valid, but the local verifier
cannot know by itself whether a later recovery has superseded it. Production
therefore requires a separately operated current-descriptor registry or other
independent monotonic publication channel.

The implemented standalone registry stores root-signed public descriptors only.
It accepts epoch one as the initial state, then requires an exact one-epoch
advance and the digest of the current descriptor. It preserves append-only
history and rejects rollback, same-epoch equivocation, gaps, broken continuity,
workspace changes, tampering and capacity exhaustion. Its public service bounds
descriptor bodies, disables generated documentation, returns no recovery
secrets and refuses non-loopback operation without both TLS and a publication
token of at least 32 characters. The token is supplied through
`TESSARIS_ACCOUNT_REGISTRY_PUBLISH_TOKEN`, never as a command-line argument.

Set `TESSARIS_ACCOUNT_DESCRIPTOR_REGISTRY_URL` on the backend to make signed
AION desktop sessions resolve current account state from the separately running
service. Production registry URLs must use HTTPS. The registry client retains a
local anti-rollback memory but never uses that cache as a freshness fallback:
an unreachable registry fails closed. The remaining application session
issuers must bind the same account ID, recovery epoch and device authority.

The registry is run separately with:

```text
backend/scripts/run_application_account_descriptor_registry.py \
  --database /approved/registry/account-descriptors.sqlite3 \
  --host registry.example \
  --port 8743 \
  --ssl-certfile /approved/tls/fullchain.pem \
  --ssl-keyfile /approved/tls/private-key.pem
```

The approved secret store must inject
`TESSARIS_ACCOUNT_REGISTRY_PUBLISH_TOKEN` into the registry process. Reading
current public descriptors does not require that publication credential.

This implementation does not make a registry running on the same laptop
independent. Until it is deployed under separate operational control, the
remaining session issuers are connected and a live clean-device exercise has
passed, Tessaris must describe this as an implemented local recovery and
registry foundation rather than production application-account recovery.

Deployment-managed validator-finality keys remain outside this recovery kit in
approved secret custody. Account recovery does not restore or copy validator
credentials and does not grant validator authority.

## Verified local behaviour

The focused regression proves:

- encrypted off-device kit creation without plaintext private-key disclosure;
- signed public descriptor and stable account-ID verification;
- wrong-password, tampered-kit and tampered-descriptor rejection;
- expected-account binding;
- monotonic recovery-epoch advancement;
- old-device and stale-epoch rejection;
- clean-target enforcement;
- exact descriptor-chain continuity after recovery;
- append-only monotonic registry publication and idempotent replay;
- rollback, same-epoch conflict, gap, tampering and unsafe-path rejection;
- bounded standalone registry API behavior;
- HTTPS-only production registry-client configuration;
- persistent client-side rollback detection; and
- fail-closed behavior when the current registry is unavailable.

These tests are local protocol evidence, not proof of independent publication,
live multi-device revocation or production availability.
