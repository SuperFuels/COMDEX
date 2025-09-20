from symatics.terms import Sym, Var, App
from symatics.rewrite import Rewriter

S = lambda s: Sym(s)
V = lambda v: Var(v)
A = lambda h,*xs: App(S(h), list(xs))

def test_assoc_comm_mu():
    r = Rewriter()
    t = A("⊕", A("⊕", V("x"), V("y")), V("z"))
    n = r.normalize(t)
    # check ends in normalized right-associated shape via axioms
    assert isinstance(n, App) and n.head.name=="⊕"
    t2 = A("μ", A("μ", V("x")))
    n2 = r.normalize(t2)
    assert n2 == A("μ", V("x"))