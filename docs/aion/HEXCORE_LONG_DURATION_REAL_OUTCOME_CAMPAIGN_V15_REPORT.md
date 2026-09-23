# Arena v15: Long-Duration Real-Outcome Campaign

Arena v15 replaces compressed milestone simulations with a wall-clock control
plane. It cannot become eligible before 24 real elapsed hours and twelve
independently checkpointed cycles.

Each cycle commits its intended information actions before contacting four
independently maintained authorities (CPython, Node.js, PyPI and Open-Meteo),
runs protected AION verification in a fresh process, commits a transactional
database outcome, attributes connectivity separately from source change, and
updates a learned monitoring interval from observed change/failure rates. Every
outcome is written to an append-only hashed ledger and the resumable state is
atomically replaced.

The campaign is deliberately not promoted at launch. Early execution must
report `BLOCKED_UNTIL_WALL_CLOCK_AND_OUTCOME_GATES_PASS`; this proves that a
tight internal loop cannot impersonate duration. After the wall-clock and
cycle gates pass, the result is only eligible for CAU review. Independent
administration remains a separate authority gate.
