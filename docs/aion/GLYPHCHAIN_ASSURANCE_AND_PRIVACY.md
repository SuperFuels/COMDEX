# GlyphChain assurance and privacy boundary

## Supported assurance levels

| Displayed state | What Tessaris has verified | What it does not claim |
|---|---|---|
| Local evidence created | The document, signer commitments and audit history have been hashed and signed by the originating Tessaris device. | Network publication, delivery, legal enforceability or quorum finality. |
| Ledger committed · quorum pending | The exact proof transaction is stored in a GlyphChain ledger block and its Merkle inclusion path verifies. | Agreement by a validator quorum. |
| Signatures valid · trust anchor not supplied | The certificate's validator membership, Ed25519 votes and quorum power are internally valid. | That the validator set is the legitimate GlyphChain set. |
| Trust-anchored quorum final | The v2 certificate is valid against a separately supplied checkpoint and signs the exact ledger commitment and transaction root containing the proof. | Legal validity, qualified electronic-signature status, identity assurance beyond the configured signing policy, or uninterrupted public-network availability. |

The application must not shorten these distinct states to a generic “blockchain
certified” label. A ledger commitment is not quorum finality, and a certificate
carried inside a receipt cannot appoint its own trust anchor.

## Data placed on GlyphChain

GlyphChain stores commitments and protocol metadata. The document body, signer
name, signer email address, message body, delivery attachment and private Legal
matter record are not written into the proof transaction. The transaction binds
opaque identifiers and hashes for the document, signed-copy manifest, ordered
signer commitments and terminal audit event.

Anyone who obtains the private document and portable receipt can test whether
the bytes match the public commitment. The commitment is not encryption and
must not be presented as making a weak or predictable document secret.

## Local data and key separation

- Legal matter and envelope records use AES-256-GCM and production Keychain
  custody.
- The Legal proof device identity is a dedicated Ed25519 key and is not the
  validator-finality identity.
- P2P transport authentication uses a separate Ed25519 key.
- Validator quorum-finality votes use a separate Ed25519 key anchored in the
  validator checkpoint. Startup rejects reuse of the P2P transport key as the
  finality key.
- A normal desktop is a light node. Relay and validator duties require explicit
  local approval; installing Tessaris does not silently contribute public
  bandwidth or consensus votes.

## Retention and deletion

Local Legal records follow the configured retention schedule and legal holds.
Deletion requires a portable export and an exact confirmation, then leaves an
encrypted, content-free destruction receipt. Deleting local content does not
erase a public commitment or transaction hash from a distributed ledger. That
distinction must be disclosed before proof submission.

## Claims that remain prohibited

Until separately assessed and approved, Tessaris must not claim:

- qualified electronic signature or qualified trust-service status;
- guaranteed legal enforceability in every jurisdiction;
- anonymous or untraceable network use;
- permanent availability solely because a proof was submitted;
- production-grade decentralisation before the multi-device network gates pass;
- that a local development checkpoint is an independently distributed trust
  anchor; or
- that Photon credits or currency are required for Legal document proof.

## Production publication gate

This document, the network-participation guide, supported retention and recovery
commitments, the current validator checkpoint file, and its independently
published checkpoint ID must be versioned with every production release.
