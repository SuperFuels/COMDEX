# Arena v16: Open-Pixel Neural Policy — Governed Negative Result

Arena v16 removed two Arena-v14 scaffolds simultaneously: no explicit task
identifier and no hand-engineered position or angular feature was provided at
inference. A 49,526-parameter network received only temporally separated RGB
frames, inferred the physical family and proposed an action through a
task-conditioned learned head.

The initial grayscale model was rejected at 0/15 control success. A stronger
color-temporal model reached MountainCar 5/5 but failed CartPole and transferred
poorly to Acrobot. Three governed dataset-aggregation rounds then exposed the
challenger to its own failure states and added verified corrective labels. A
temporary invalid-action failure caused by one task misclassification was
caught by Gymnasium and led to an absolute action-contract gate.

Final results:

| Measure | Result |
|---|---:|
| Raw-pixel task-binding accuracy | 99.89% |
| Training action imitation | 90.69% |
| MountainCar sealed success | 5/5 |
| Acrobot sealed success | 2/5 |
| CartPole sealed success | 0/5 |
| Overall sealed success | 7/15 |
| OOD abstention | 2/2 |
| Unsafe actions after contract gate | 0 |

The challenger was rejected and no champion was changed. The result establishes
that open visual family recognition is already achievable, but action imitation
from compact frame pairs does not learn a sufficiently stable dynamics model.
Adding more correction data did not close the gap. The next viable architecture
must predict latent state transitions and consequences, then plan or control in
that learned latent space. Continuing to scale behavioral cloning would be a
low-leverage repetition of the same failed assumption.

This is a bounded negative result over public Gymnasium tasks, not evidence of
general visual understanding, robotics or AGI.
