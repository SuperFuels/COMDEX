# TN01 Mechanics Note (Audit Narrative)

## What TN01 is (model-only)
TN01 implements a 1D wavepacket propagation proxy with a controllable barrier.

- State: complex wavefunction ψ(x)
- Barrier: a potential window V(x)=V0 on indices [b0:b1)
- Observable: transmission T(t) = Σ_{x >= right0} |ψ(x,t)|^2  (after normalization)
- Knob: V0(t) (barrier height), controlled by a bounded controller

This is **not** a claim about physical quantum tunneling. It is a deterministic lattice-model test of
**programmable barrier transmission**.

## Mapping: “Tessaris language” → “Code mechanism”
- “Barrier / forbidden region” → `V[b0:b1] = v0` in `TUNNEL/src/programmable_tunnel/sim.py`
- “Penetration / transmission” → `T = prob[right0:].sum()`
- “Controller authority” → `TransmissionLockController.step()` updates `v0` based on (T - T_target)
- “Baselines” → open_loop (no controller), random_jitter_barrier (noise-only V0 updates)

## Internal references (conceptual, not required to run TN01)
- Tessaris_Extended_Causal_Fabric — Section 5 “Multiverse Connectivity”
  (used only as narrative mapping: boundary matching / state-space migration analog)
- Tessaris L-Series notes (Planck-scale cutoff / lattice grain)
  (used only to justify discrete barrier representation + dx/dt as “grain” parameters)

## Audit hooks (what to show)
- Repro command:
  env PYTHONPATH=$PWD/TUNNEL/src python -m pytest TUNNEL/tests/programmable_tunnel/test_tn01_transmission_lock.py -q
- Artifacts:
  TUNNEL/artifacts/programmable_tunnel/TN01/<RUN_HASH>/{run.json,metrics.csv,meta.json,config.json}
