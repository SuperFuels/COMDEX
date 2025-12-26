EVIDENCE_BLOCK
Claim: TN01 Transmission Lock — closed-loop barrier controller tunes transmission to a target rate and beats baselines.
Scope: TUNNEL / TN01
Git_Commit: <git rev-parse --short HEAD>
Repro_Command: env PYTHONPATH=$PWD/TUNNEL/src python -m pytest TUNNEL/tests/programmable_tunnel/test_tn01_transmission_lock.py -q

Artifact_Paths:
  - TUNNEL/artifacts/programmable_tunnel/TN01/<RUN_HASH>/run.json
  - TUNNEL/artifacts/programmable_tunnel/TN01/<RUN_HASH>/metrics.csv
  - TUNNEL/artifacts/programmable_tunnel/TN01/<RUN_HASH>/meta.json

Pinned_Runs:
  - TN01 tessaris_transmission_lock: <RUN_HASH>
  - TN01 open_loop: <RUN_HASH>
  - TN01 random_jitter_barrier: <RUN_HASH>

Results:
  - Tessaris: T_final=..., T_target=..., T_err_final=..., V0_initial=..., V0_final=...
  - Open-loop: ...
  - Random jitter: ...

Notes:
  - Model-only: discrete wavepacket propagation with a potential barrier; no physical tunneling claims.
  - Deterministic seed/config written to artifacts.
/EVIDENCE_BLOCK

Theory_Refs:
  - TUNNEL/docs/TN01_MECHANICS_NOTE.md
  - Tessaris_Extended_Causal_Fabric (Oct 2025), Section 5
  - Tessaris L-Series (Oct 2025), lattice grain / cutoff discussion
