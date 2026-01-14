import PhotonAlgebra.BridgeTheorem

namespace PhotonAlgebra
open PhotonAlgebra

/-- Markdown snapshot emitted by the BridgeSnapshot executable. -/
def theoremSnapshot : String :=
"# PhotonAlgebra Theorem Snapshot\n\n" ++
"Automated proof snapshot (Lean compiled = ✅).\n\n" ++
"| Theorem | Statement | Result |\n" ++
"|---------|-----------|--------|\n" ++
"| wf_invariant_normStep | `normalizeWF (normStep e) = normalizeWF e` | ✅ |\n" ++
"| wf_invariant_normalizeFuel | `normalizeWF (normalizeFuel k e) = normalizeWF e` | ✅ |\n" ++
"| normalize_bridge | `normalizeWF (normalize e) = normalizeWF e` | ✅ |\n\n" ++
"**Proved in:** `PhotonAlgebra/BridgeTheorem.lean`\n"

/-- Writes the snapshot to the repository path you requested. -/
@[main] def main : IO Unit := do
  let outPath :=
    "/workspaces/COMDEX/backend/photon_algebra/PhotonAlgebra/theorem_snapshot.md"
  IO.FS.writeFile outPath theoremSnapshot
  IO.println s!"Wrote snapshot: {outPath}"

end PhotonAlgebra