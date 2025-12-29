import Lake
open Lake DSL

package tessaris_lean where
  srcDir := "."

@[default_target]
lean_lib Tessaris where
  roots := #[`Tessaris]
  precompileModules := false
