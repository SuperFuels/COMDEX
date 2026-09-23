# HexCore Arena v9: Public Pixel-Physics Transfer

Arena v9 is internally promoted as
`procedure_public_pixel_physics_transfer_v9_627e18f70a39`.

Farama Gymnasium 1.2.3 owns the MountainCar-v0 and CartPole-v1 dynamics,
termination and reward. AION discards numerical observations and acts from
rendered RGB frames only. Four bounded programs per environment competed on
three development seeds. Outcomes selected `momentum_feedback` for MountainCar
and the predictive CartPole rule

\[
u_t=\mathbf{1}[\theta_t+2(\theta_t-\theta_{t-1})>0].
\]

The frozen programs were evaluated on six fresh seeds per environment. Every
action was SHA-256 committed before execution. Identical zero-experience
controls received the same environments and budgets but used the first
unevaluated program.

| Measure | Result |
|---|---:|
| Public authority | Farama Gymnasium 1.2.3 |
| Public physics families | 2 |
| Development / sealed seeds | 6 / 12 |
| Learned success | 100% |
| Weakest-family success | 100% |
| Zero-experience success | 0% |
| Success lift | +100 points |
| Pre-action commitments | 3,706 |
| Numerical observations used | 0 |
| Unknown Acrobot actions executed | 0 |
| Unknown-schema abstention | Passed |
| Unsafe actions / live writes | 0 / 0 |
| Restart relearning | 0 |

The installed MountainCar authority source is committed as
`f97a9b162f329b6c8a1234b25d3df620fd45186fa333b7a789c1568265866309`.

This is public third-party simulated physics and a stronger authority boundary
than an AION-authored simulator. Development still selected the environments,
candidate grammar, seeds and gates. It is not independently administered
certification, real robotic action, unrestricted reinforcement learning or AGI.

