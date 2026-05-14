from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List
from .terms import Term, Var, Sym, App
from .axioms import AXIOMS, Law

Subst = Dict[str, Term]

def _match(pat: Term, t: Term, env: Optional[Subst]=None) -> Optional[Subst]:
    env = {} if env is None else dict(env)
    if isinstance(pat, Var):
        if pat.name in env:
            return env if env[pat.name]==t else None
        env[pat.name] = t
        return env
    if isinstance(pat, Sym) and isinstance(t, Sym):
        return env if pat.name==t.name else None
    if isinstance(pat, App) and isinstance(t, App):
        # match head
        h = _match(pat.head, t.head, env)
        if h is None: return None
        if len(pat.args)!=len(t.args): return None
        for pa, ta in zip(pat.args, t.args):
            h = _match(pa, ta, h)
            if h is None: return None
        return h
    return None

def _subst(term: Term, env: Subst) -> Term:
    from copy import deepcopy
    if isinstance(term, Var):
        return env.get(term.name, term)
    if isinstance(term, Sym):
        return term
    if isinstance(term, App):
        return App(_subst(term.head, env), [ _subst(a, env) for a in term.args ])
    return term

@dataclass
class Rewriter:
    max_steps: int = 128

    def rewrite_once(self, t: Term) -> Optional[Term]:
        for law in AXIOMS:
            m = _match(law.lhs, t)
            if m is not None and (law.guard is None or law.guard(m)):
                return _subst(law.rhs, m)
        if isinstance(t, App):
            # try to rewrite children
            new_head = self.rewrite_once(t.head) or t.head
            new_args = []
            changed = False
            for a in t.args:
                na = self.rewrite_once(a)
                if na is not None:
                    changed = True
                    new_args.append(na)
                else:
                    new_args.append(a)
            if changed or new_head is not t.head:
                return App(new_head, new_args)
        return None

    def normalize(self, t: Term) -> Term:
        steps = 0
        cur = t
        while steps < self.max_steps:
            nxt = self.rewrite_once(cur)
            if nxt is None:
                return cur
            cur = nxt
            steps += 1
        return cur