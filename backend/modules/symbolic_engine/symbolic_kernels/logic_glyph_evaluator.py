# backend/modules/symbolic_engine/symbolic_kernels/logic_glyph_evaluator.py

from typing import Any, Dict, Union
from .logic_glyphs import AndGlyph, OrGlyph, NotGlyph, ImplicationGlyph, LogicGlyph

def evaluate_logic_tree(tree: Union[LogicGlyph, str], context: Dict[str, bool]) -> bool:
    """
    Evaluates a parsed logic tree given a truth assignment context.
    Leaves (str) must map to boolean values in `context`.
    """
    if isinstance(tree, str):
        if tree not in context:
            raise ValueError(f"Symbol '{tree}' has no assigned truth value.")
        return context[tree]

    if isinstance(tree, NotGlyph):
        return not evaluate_logic_tree(tree.operands[0], context)

    if isinstance(tree, AndGlyph):
        return all(evaluate_logic_tree(op, context) for op in tree.operands)

    if isinstance(tree, OrGlyph):
        return any(evaluate_logic_tree(op, context) for op in tree.operands)

    if isinstance(tree, ImplicationGlyph):
        premise, conclusion = tree.operands
        return not evaluate_logic_tree(premise, context) or evaluate_logic_tree(conclusion, context)

    raise TypeError(f"Unsupported glyph type for evaluation: {type(tree)}")