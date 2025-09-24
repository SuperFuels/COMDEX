# backend/modules/lean/symatics_to_lean.py

def symatics_to_lean(expr: str, name: str = "symatics_test", use_prelude: bool = True) -> str:
    """
    Translate a Symatics algebra expression into a Lean axiom/theorem.
    By default, it imports the Symatics prelude (operators like ⊕, ↑, ↓).
    """
    prelude = "import ./symatics_prelude\n\n" if use_prelude else ""
    return f"""{prelude}axiom {name} : {expr}"""