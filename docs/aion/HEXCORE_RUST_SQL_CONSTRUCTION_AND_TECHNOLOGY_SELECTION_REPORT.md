# HexCore Rust/SQL Construction and Technology Selection

## Outcome

AION progressed from language execution and repair into bounded new-program
construction and evidence-scored technology selection. CAU promoted:

`procedure_rust_sql_construction_and_selection_b949b03fda6e`

## Rust construction

From a behavioral contract, the proposal substrate generated a complete
dependency-free Rust command-line program. Independent authority compiled it
with warnings denied and evaluated positive values, negative values, empty
input, invalid integers and signed-64-bit overflow.

The retained program produced exact count, checked sum, minimum and maximum
results and failed closed on empty, invalid and overflowing inputs. Static
authority rejected unsafe blocks, subprocess execution and network access
before execution.

## SQL construction

AION generated a SQLite-compatible transactional ledger with accounts,
transfers, non-empty owners, non-negative balances, positive transfers,
self-transfer prevention, foreign keys and source/destination time indexes.

The evaluator discovered AION's invented relationship-column names from schema
metadata rather than imposing a hidden naming convention. Valid transactions
committed; negative balances, empty owners, missing accounts, self-transfers and
non-positive transfers were rejected. Destructive SQL, disabled foreign keys
and extension loading were blocked before execution.

## Technology selection

AION selected among Rust, Python, TypeScript, SQL+Rust and SQL+Python for six
unfamiliar requirement profiles. An independent utility scorer evaluated
performance, memory safety, iteration speed, browser execution, relational
integrity and ML/data ecosystem value.

| Project | Selected technology |
|---|---|
| Low-latency safe parser | Rust |
| Research notebook | Python |
| Browser console | TypeScript |
| Financial ledger | SQL+Rust |
| Audited ETL | SQL+Python |
| Embedded gateway | Rust |

Selection accuracy and weakest-case success were both 100%, with a rationale
and rejected alternative for every decision.

## Claim boundary

This demonstrates construction and verified execution for one bounded Rust
program and one bounded SQL schema, plus selection over six engineered project
profiles. It does not establish broad Rust ownership/lifetime expertise,
production database administration, unrestricted system design or general
architecture judgment.
