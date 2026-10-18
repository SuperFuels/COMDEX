# AION Final Bracketed Cube-Lift Attempt — 2026-08-08

## Verdict

The final fresh-world NVIDIA Isaac Lab attempt did **not** lift the cube.

- Strict lift successes: **0/1**
- Maximum cube height: **0.052057 m**
- Starting cube height: **0.052057 m**
- Net cube elevation: **0.000000 m**
- Required success height: **greater than 0.10 m**
- Unsafe outcomes: **0**
- Evaluation length: **350 steps**

The controller reached one-sided object contact on three frames, issued one
causal reopen-and-center correction, but did not recover opposed two-finger
contact. It never closed the fingers, never acquired an attachment signature,
and therefore correctly refused to execute an unverified lift.

## Final controller changes

The final attempt used symmetric tactile bracketing: a second correction would
test the opposite side of the original approach instead of continuing farther
in the first direction. It also routed verified grasp and lift phases through
the settled Cartesian controller rather than the older joint-space lift path.

The second bracket was not reached in this episode because persistent
one-sided evidence did not recur after the first correction.

## Strongest result retained from this development cycle

The best sealed run remains
`object_filtered_phase2_cartesian_20260808_v1`: it produced 19 consecutive
frames of genuine, object-filtered, opposed fingertip contact, with realistic
finger width and stable forces. It missed the deliberately strict attachment
balance threshold and did not lift. This proves the geometry can acquire a
two-finger grasp, but it is not repeatable enough to call the task solved.

## Engineering conclusion

The remaining blocker is grasp acquisition reliability, not the upward lift
command. Fresh worlds with the same nominal seed still reach materially
different late-contact states. The hand can acquire secure-looking opposed
contact, but the last centimetres of approach and tactile recentering are not
stable enough to reproduce it reliably.

No further paid retry was launched. Both NVIDIA instances were stopped after
the evidence was copied locally.

## Verification

All 33 focused local controller, tactile, and contract-filter tests passed
before the run. The immutable JSON uses post-action cube height greater than
0.10 m as the independent success authority. The NPZ includes per-step true
post-action cube position and private policy-mode diagnostics; neither was
available to the policy as input.
