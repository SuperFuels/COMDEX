import Lake
open Lake DSL

package symatics_bridge_only where
  srcDir := "."

@[default_target]
lean_lib SymaticsBridge where
  roots := #[`SymaticsBridge]
  precompileModules := false
