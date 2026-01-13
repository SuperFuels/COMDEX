-- backend/modules/lean/workspace/lakefile.lean
import Lake
open Lake DSL

package tessaris_lean where
  srcDir := "."

@[default_target]
lean_lib Tessaris where
  roots := #[`Tessaris]
  precompileModules := false

lean_lib SymaticsBridge where
  roots := #[`SymaticsBridge]
  precompileModules := false

-- --- Photon Algebra (PA-core) ---
lean_lib PhotonAlgebra where
  -- lake is invoked from: backend/modules/lean/workspace
  -- photon algebra lives at: backend/photon_algebra
  srcDir := "../../../photon_algebra"
  roots := #[`PhotonAlgebra]
  precompileModules := false

lean_exe photon_algebra_test where
  srcDir := "../../../photon_algebra"
  root := `PhotonAlgebra.Test
-- --- end Photon Algebra ---