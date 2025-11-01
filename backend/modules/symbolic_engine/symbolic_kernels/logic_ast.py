# backend/modules/symbolic_engine/symbolic_kernels/logic_ast.py

from typing import Any, Dict, List, Optional
from copy import deepcopy
from .logic_glyphs import (
    LogicGlyph, AndGlyph, OrGlyph, NotGlyph, ImplicationGlyph,
    ProvableGlyph, EntailmentGlyph, TrueGlyph, FalseGlyph, SymbolGlyph
)


class LogicNode:
    def __init__(
        self,
        op: str,
        children: Optional[List['LogicNode']] = None,
        symbol: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.op = op
        self.children = children or []
        self.symbol = symbol
        self.metadata = metadata or {}

    def __repr__(self):
        if self.symbol:
            return self.symbol
        if not self.children:
            return f"{self.op}()"
        return f"{self.op}({', '.join(map(str, self.children))})"

    def __eq__(self, other):
        if not isinstance(other, LogicNode):
            return False
        return (
            self.op == other.op
            and self.symbol == other.symbol
            and self.metadata == other.metadata
            and self.children == other.children
        )

    def simplify(self) -> 'LogicNode':
        """
        Simplifies logic expressions using classical simplification rules.
        Examples:
          - A ∧ ⊤ -> A
          - A ∨ ⊥ -> A
          - ¬¬A -> A
        """
        simplified = LogicNode(self.op, [child.simplify() for child in self.children], self.symbol, deepcopy(self.metadata))

        if simplified.op == '¬':
            child = simplified.children[0]
            if child.op == '¬':
                return child.children[0]  # ¬¬A -> A

        elif simplified.op == '∧':
            left, right = simplified.children
            if right.op == '⊤':
                return left
            if left.op == '⊤':
                return right
            if right.op == '⊥' or left.op == '⊥':
                return LogicNode('⊥')

        elif simplified.op == '∨':
            left, right = simplified.children
            if right.op == '⊥':
                return left
            if left.op == '⊥':
                return right
            if left.op == '⊤' or right.op == '⊤':
                return LogicNode('⊤')

        return simplified

    def mutate(self, mutation_fn) -> 'LogicNode':
        """
        Applies a symbolic transformation function recursively.
        `mutation_fn` takes a LogicNode and returns a modified node.
        """
        mutated_children = [child.mutate(mutation_fn) for child in self.children]
        mutated_node = LogicNode(self.op, mutated_children, self.symbol, deepcopy(self.metadata))
        return mutation_fn(mutated_node)

    def to_glyph(self) -> LogicGlyph:
        if self.op == '->':
            return ImplicationGlyph(*(child.to_glyph() for child in self.children))
        elif self.op == '∧':
            return AndGlyph(*(child.to_glyph() for child in self.children))
        elif self.op == '∨':
            return OrGlyph(*(child.to_glyph() for child in self.children))
        elif self.op == '¬':
            return NotGlyph(self.children[0].to_glyph())
        elif self.op == '⊤':
            return TrueGlyph()
        elif self.op == '⊥':
            return FalseGlyph()
        elif self.op == '⊢':
            assumptions, conclusion = self.children
            return ProvableGlyph(assumptions.to_glyph(), conclusion.to_glyph())
        elif self.op == '⊨':
            assumptions, conclusion = self.children
            return EntailmentGlyph(assumptions.to_glyph(), conclusion.to_glyph())
        elif self.symbol:
            return SymbolGlyph(self.symbol)
        else:
            raise ValueError(f"Unsupported operation: {self.op}")

    @staticmethod
    def from_glyph(glyph: LogicGlyph) -> 'LogicNode':
        if isinstance(glyph, SymbolGlyph):
            return LogicNode(op='SYMBOL', symbol=glyph.symbol)
        elif isinstance(glyph, TrueGlyph):
            return LogicNode(op='⊤')
        elif isinstance(glyph, FalseGlyph):
            return LogicNode(op='⊥')
        elif isinstance(glyph, NotGlyph):
            return LogicNode(op='¬', children=[LogicNode.from_glyph(glyph.operands[0])])
        elif isinstance(glyph, AndGlyph):
            return LogicNode(op='∧', children=[LogicNode.from_glyph(op) for op in glyph.operands])
        elif isinstance(glyph, OrGlyph):
            return LogicNode(op='∨', children=[LogicNode.from_glyph(op) for op in glyph.operands])
        elif isinstance(glyph, ImplicationGlyph):
            return LogicNode(op='->', children=[LogicNode.from_glyph(op) for op in glyph.operands])
        elif isinstance(glyph, ProvableGlyph):
            return LogicNode(op='⊢', children=[LogicNode.from_glyph(glyph.operands[0]), LogicNode.from_glyph(glyph.operands[1])])
        elif isinstance(glyph, EntailmentGlyph):
            return LogicNode(op='⊨', children=[LogicNode.from_glyph(glyph.operands[0]), LogicNode.from_glyph(glyph.operands[1])])
        else:
            raise TypeError(f"Unsupported glyph type: {type(glyph)}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "op": self.op,
            "symbol": self.symbol,
            "metadata": self.metadata,
            "children": [child.to_dict() for child in self.children],
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'LogicNode':
        return LogicNode(
            op=data["op"],
            symbol=data.get("symbol"),
            metadata=data.get("metadata", {}),
            children=[LogicNode.from_dict(child) for child in data.get("children", [])],
        )


class LogicTree:
    def __init__(self, root: LogicNode):
        self.root = root

    def __repr__(self):
        return str(self.root)

    def __eq__(self, other):
        if not isinstance(other, LogicTree):
            return False
        return self.root == other.root

    def to_glyph(self) -> LogicGlyph:
        return self.root.to_glyph()

    @staticmethod
    def from_glyph(glyph: LogicGlyph) -> 'LogicTree':
        return LogicTree(LogicNode.from_glyph(glyph))

    def simplify(self) -> 'LogicTree':
        return LogicTree(self.root.simplify())

    def mutate(self, mutation_fn) -> 'LogicTree':
        return LogicTree(self.root.mutate(mutation_fn))

    def find_symbols(self) -> List[str]:
        symbols = []

        def visit(node: LogicNode):
            if node.symbol:
                symbols.append(node.symbol)
            for child in node.children:
                visit(child)

        visit(self.root)
        return sorted(set(symbols))

    def to_dict(self) -> Dict:
        return self.root.to_dict()

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'LogicTree':
        return LogicTree(LogicNode.from_dict(data))