# backend/modules/demo/photon_demo_semantics.py
import sympy as sp
import re
from backend.photon.rewriter import rewriter, Grad, _glyph_to_sympy, GradPower

print("⚡ Photon Proof Playground ⚡")
print("----------------------------------\n")


# --- Helpers ---
SUPERSCRIPTS = {
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5",
    "6": "6",
    "7": "7",
    "8": "8",
    "9": "9",
}


def sup_to_int(s: str) -> int:
    """Convert Unicode superscripts into an integer string."""
    return int("".join(SUPERSCRIPTS.get(ch, ch) for ch in s))


def expand_grad_power(expr: str):
    """
    Expand ∇nx into GradPower(x, n).
    Examples:
      ∇2a     -> GradPower(a,2)
      ∇3a     -> GradPower(a,3)
      ∇2a     -> GradPower(a,2)
    """

    def repl_var(match):
        power_str = match.group(1)
        var = match.group(2)
        try:
            power = sup_to_int(power_str)
        except ValueError:
            power = int(power_str)
        return f"GradPower({var}, {power})"

    def repl_func(match):
        power_str = match.group(1)
        arg = match.group(2)
        try:
            power = sup_to_int(power_str)
        except ValueError:
            power = int(power_str)
        return f"GradPower({arg}, {power})"

    # ∇2a, ∇3a
    expr = re.sub(r"∇([234567890-9]+)([a-zA-Z]\w*)", repl_var, expr)
    # ∇2(f(x))
    expr = re.sub(r"∇([234567890-9]+)\(([^)]+)\)", repl_func, expr)

    # Handle ∇f(x) -> Grad(f(x))
    expr = re.sub(r"∇([a-zA-Z]\w*)\(([^)]+)\)", r"Grad(\1(\2))", expr)
    # Bare ∇f -> Grad(f)
    expr = re.sub(r"∇([a-zA-Z]\w*)", r"Grad(\1)", expr)

    return expr


def pretty_grad(expr):
    """
    Pretty-print GradPower back into ∇n(arg).
    """
    if isinstance(expr, GradPower):
        arg, n = expr.args
        sup_map = {"2": "2", "3": "3", "4": "4", "5": "5"}
        n_str = sup_map.get(str(n), f"^{n}")
        return f"∇{n_str}{pretty_grad(arg)}"
    if isinstance(expr, Grad):
        return f"∇({pretty_grad(expr.args[0])})"
    if isinstance(expr, sp.Symbol):
        return str(expr)
    if isinstance(expr, sp.Basic):
        return str(expr)
    return str(expr)


def normalize(expr: str):
    """Expand shorthand, then normalize via Photon."""
    expr = expand_grad_power(expr)
    return rewriter.normalize(expr)


def prove_equiv(lhs: str, rhs: str, title: str):
    """Pretty demo of equivalence check with normalization trace."""
    print(f"🔹 Demo: {title}")
    print(f"   Input: {lhs}")
    norm_lhs = normalize(lhs)
    print(f"   Normalized LHS: {pretty_grad(norm_lhs)}")
    print(f"   Target: {rhs}")
    norm_rhs = normalize(rhs)
    print(f"   Normalized RHS: {pretty_grad(norm_rhs)}")
    try:
        result = "✅ Equivalent" if sp.simplify(norm_lhs - norm_rhs) == 0 else "❌ Not equivalent"
    except Exception:
        result = "✅ Equivalent" if str(norm_lhs) == str(norm_rhs) else "❌ Not equivalent"
    print(f"   Result: {result}\n")


# --- Run demos (axioms) ---
prove_equiv("a ⊕ b", "b ⊕ a", "Commutativity")
prove_equiv("(a ⊕ b) ⊕ c", "a ⊕ (b ⊕ c)", "Associativity")
prove_equiv("a ⊗ (b ⊕ c)", "(a ⊗ b) ⊕ (a ⊗ c)", "Distributivity")
prove_equiv("a ⊕ 0", "a", "Additive Identity")
prove_equiv("a ⊗ 1", "a", "Multiplicative Identity")
prove_equiv("a ⊗ 0", "0", "Multiplicative Annihilation")

# --- Gradient demos ---
prove_equiv("∇(a ⊕ b)", "∇a ⊕ ∇b", "Gradient Add Rule")
prove_equiv("∇(a ⊗ b)", "(∇a ⊗ b) ⊕ (a ⊗ ∇b)", "Gradient Product Rule")
prove_equiv("∇(∇a)", "∇2a", "Second Derivative")
prove_equiv("∇(∇(∇a))", "∇3a", "Third Derivative")

# --- Advanced demos ---
prove_equiv("∇(f(g(x)))", "Compose(Grad(f), g(x)) ⊗ Compose(Grad(g), x)", "Chain Rule")
prove_equiv("∇((x ⊗ y) ⊕ z)", "(∇x ⊗ y) ⊕ (x ⊗ ∇y) ⊕ ∇z", "Multi-variable Gradient Distribution")

# --- Nth derivative loop ---
for n in range(1, 6):
    if n == 1:
        lhs = "∇a"
        rhs = "∇a"
    else:
        # Build nested gradient correctly: ∇(∇(...∇a...))
        inner = "a"
        for _ in range(n):
            inner = f"∇({inner})"
        lhs = inner
        rhs = f"∇{n}a"
    prove_equiv(lhs, rhs, f"{n}th Derivative Consistency")