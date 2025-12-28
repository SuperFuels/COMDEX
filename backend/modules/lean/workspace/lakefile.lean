import Lake
open Lake DSL

package tessaris_lean where
  srcDir := "."

lean_lib Tessaris where
  roots := #[`Tessaris]
  precompileModules := false
