# AION Open Micro-Operation Invention

## Outcome

AION has accepted a private implementation of a transformation that was not
expressible by its promoted action-atom compiler:

`ROBUST_MEDIAN_PAIRWISE_TREND`

The micro-operation is implemented as restricted pure-function source and is
currently withheld from the compiler registry pending three later public
consequences.

| Measure | Result |
|---|---:|
| Private micro-operations invented | 1 |
| Candidate implementations | 3 |
| Generated algebraic properties | 6 |
| Algebraic properties passed | 6/6 |
| Security implementations rejected | 8/8 |
| Development success | 1/1 |
| Source-disjoint transfers | 2/2 |
| Independent public authorities | 3 |
| Error against independent oracle | 0 across all three |
| Compiler installation before later authority | 0 |
| Later authority confirmations | 3/3 |
| Cold-runtime reconstruction | passed |
| Ambient authority added | 0 |
| Arbitrary/unsafe execution and live writes | 0 |

## Compiler residual

The promoted temporal-projection atom can infer canonical numerical series but
the meta-compiler had no robust trend primitive. Endpoint slope and ordinary
least squares are brittle under adversarial contamination, and the existing
micro-operation vocabulary could not express pairwise median estimation.

AION synthesized three private implementations. The endpoint estimator was
initially attractive because it was shorter, but a generated boundary-outlier
counterexample falsified it. Ordinary least squares requested an unsupported
aggregate call and failed the restricted-source validator. The surviving
implementation enumerates all pairwise slopes and returns their median.

## Self-generated executable semantics

The selected source passed:

1. Translation invariance.
2. Positive-scale equivariance.
3. Boundary-outlier robustness.
4. Zero slope for a constant series.
5. Abstention below three observations.
6. Deterministic re-execution.

Eight hostile implementations were rejected before execution: imports, file
opening, dynamic execution, dunder access, unbounded loops, shell calls,
unapproved attribute mutation and secondary helper functions.

## Private execution environment

Candidate source is parsed into a restricted Python AST. Only a single `run`
entrypoint, bounded loops, arithmetic, indexing, sorting and list append are
permitted. Imports, filesystem calls, network calls, process calls, reflection,
dynamic execution and ambient object access are absent. Each property runs in a
fresh isolated Python process with a timeout and disposable working directory.
The result channel accepts one finite JSON number or explicit `null` abstention.

## Real transfer

The new implementation consumed canonical series created by the previously
promoted `TEMPORAL_NUMERIC_PROJECTION` atom:

| Authority | Observations | Invented slope | Oracle slope | Absolute error |
|---|---:|---:|---:|---:|
| World Bank GDP | 66 | 59,858,508,067.0227 | 59,858,508,067.0227 | 0 |
| Federal Reserve FRED GDP | 318 | 78.1916428571 | 78.1916428571 | 0 |
| NOAA temperature | 236 | 0.1570175439 | 0.1570175439 | 0 |

World Bank was the development authority. FRED and NOAA were source-disjoint
transfers. An independently implemented host oracle controlled scoring; the
private source could not access it.

## Promotion boundary

Development, transfer and properties authorized only a private challenger. The
source digest
`78efd13d0873be5aff46cf008afbb5728390d1478265a7cb58d47134a775cda3`
was precommitted while the compiler registry remained unchanged. After the
five-minute boundary, all three public series were reacquired through the
promoted projection atom and matched the independent oracle again. HexCore then
promoted `procedure_delayed_micro_operation_compiler_promotion_v1` and installed
the exact source and pure capability class.

A fresh `GovernedMicroOperationRuntime` verified the source digest and executed
the promoted implementation without private-state access. It returned slope
$1$ for both a clean linear series and a boundary-contaminated series, $0$ for
a constant series, and explicit `null` abstention for two observations.

## Boundary

This is bounded open micro-operation invention, not unrestricted self-coding.
Candidate synthesis grammar, allowed AST nodes, algebraic property family,
public series and independent oracle remain engineered. The next boundary is
open property-language invention: when existing semantic properties cannot
distinguish plausible implementations, AION must construct a new falsification
property from observed transfer failure and retain that critic across unrelated
future inventions.

## Artifacts

- Implementation: `backend/modules/hexcore/open_micro_operation_invention.py`
- Regression: `backend/tests/test_open_micro_operation_invention.py`
- Result: `results/hexcore_open_micro_operation_invention.json`
- Private source: `backend/modules/hexcore/data/open_micro_operation_invention/private_source.json`
- Compiler registry: `backend/modules/hexcore/data/recursive_action_runtime/micro_op_registry.json`
