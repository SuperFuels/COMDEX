# P16 — Calibration (Pilot freeze)

This bundle freezes:
- dataset registry + sha256 pin
- metrics contract (frozen pilot metric)
- preprocess contract + frozen preprocess output (sha256 pinned)

Guardrails:
- no external downloads
- deterministic preprocessing + deterministic evaluator plumbing
- no wetlab or edit-success claims
