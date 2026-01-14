import PhotonAlgebra.BridgeTheorem
import PhotonAlgebra.Phase1Theorems
import PhotonAlgebra.SnapshotStatus

namespace PhotonAlgebra

private def INFO  : String := "ℹ️ DESIGN"

def theoremSnapshot : String :=
"# PhotonAlgebra Theorems Results\n\n" ++
"Automated proof snapshot (Lean).\n\n" ++

"## Bridge\n\n" ++
"| Item | Statement | Status |\n" ++
"|---|---|---|\n" ++
"| wf_invariant_normStep | `normalizeWF (normStep e) = normalizeWF e` | " ++ status_wf_invariant_normStep ++ " |\n" ++
"| wf_invariant_normalizeFuel | `normalizeWF (normalizeFuel k e) = normalizeWF e` | " ++ status_wf_invariant_normalizeFuel ++ " |\n" ++
"| normalize_bridge | `normalizeWF (normalize e) = normalizeWF e` | " ++ status_normalize_bridge ++ " |\n\n" ++

"## Phase-1 (EqNF laws)\n\n" ++
"| Theorem | Statement | Status |\n" ++
"|---|---|---|\n" ++
"| CollapseWF | `normalizeWF (∇a) = ∇(normalizeWF a)` | " ++ status_CollapseWF ++ " |\n" ++
"| T8 | `EqNF (a ⊗ (b ⊕ c)) ((a ⊗ b) ⊕ (a ⊗ c))` | " ++ status_T8 ++ " |\n" ++
"| T9 | `EqNF (¬(¬a)) a` | " ++ status_T9 ++ " |\n" ++
"| T10 | `EqNF ((a↔b) ⊕ (a↔c)) (a↔(b⊕c))` | " ++ status_T10 ++ " |\n" ++
"| T11 | `EqNF (a↔a) a` | " ++ status_T11 ++ " |\n" ++
"| T12 | `EqNF (★(a↔b)) ((★a) ⊕ (★b))` | " ++ status_T12 ++ " |\n" ++
"| T13 | `EqNF (a ⊕ (a ⊗ b)) a` | " ++ status_T13 ++ " |\n" ++
"| T14 | `NO RULE: factoring is excluded (one-way distribution only)` | " ++ INFO ++ " |\n" ++
"| T15R | `EqNF (a ⊖ ∅) a` | " ++ status_T15R ++ " |\n" ++
"| T15L | `EqNF (∅ ⊖ a) a` | " ++ status_T15L ++ " |\n" ++
"| T15C | `EqNF (a ⊖ a) ∅` | " ++ status_T15C ++ " |\n\n" ++
"Generated from `PhotonAlgebra/SnapshotGen.lean`.\n"

#eval IO.FS.writeFile
  "/workspaces/COMDEX/backend/photon_algebra/PhotonAlgebra/theorem_snapshot.md"
  theoremSnapshot

end PhotonAlgebra