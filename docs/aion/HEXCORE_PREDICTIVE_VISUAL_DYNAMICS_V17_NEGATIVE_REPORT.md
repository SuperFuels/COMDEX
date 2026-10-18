# Arena v17: Predictive Visual Dynamics — Governed Negative Result

Arena v17 replaced Arena v16's direct behavioral-cloning objective with an
outcome-grounded latent world model. Numerical state was available only as a
private training authority. Sealed inference received temporally separated RGB
frames, inferred a task binding, reconstructed a normalized latent state,
predicted the next latent state conditional on action and proposed control from
that learned state.

The 52,442-parameter model learned a normalized latent-state RMSE of 0.0929 over
9,000 balanced frames. It nevertheless achieved only 78.14% action accuracy,
5/15 control success and a zero-success weakest family. Increasing the state
and transition losses and separately teaching the policy on true training
states did not resolve compounding closed-loop error. The challenger was
rejected; no champion changed.

Together, Arenas v16 and v17 eliminate two underpowered routes:

1. scaling pixel-to-action behavioral cloning; and
2. assuming low average one-step latent reconstruction error implies stable
   long-horizon control.

The next justified architecture is a recurrent belief-state learner with
uncertainty, long-horizon return optimization, counterfactual rollouts and
fallback to the retained verified controller bank. This is a bounded negative
result, not unrestricted visual learning, robotics or AGI.
