# File: backend/modules/codex/codex_ast_types.py

from typing import List, Dict, Any


class CodexAST:
    """
    Wrapper class for CodexLang AST nodes.
    Used for standardized manipulation, equality checking, and serialization.
    """
    def __init__(self, node: Dict[str, Any], metadata: Dict[str, Any] = None):
        self.node = node
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ast": self.node,
            "metadata": self.metadata
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CodexAST":
        return CodexAST(data.get("ast", data), metadata=data.get("metadata", {}))

    def get_type(self) -> str:
        return self.node.get("type", "")

    def __repr__(self) -> str:
        return f"CodexAST({self.node}, metadata={self.metadata})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, CodexAST):
            return False
        return self.node == other.node and self.metadata == other.metadata


# === Constructors ===

def make_variable(name: str) -> Dict[str, Any]:
    return {"type": "variable", "value": name}


def make_symbol(name: str) -> Dict[str, Any]:
    return {"type": "symbol", "value": name}


def make_call(name: str, args: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"type": "call", "name": name, "args": args}


def make_not(value: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "not", "value": value}


def make_and(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "and", "left": left, "right": right}


def make_or(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "or", "left": left, "right": right}


def make_implies(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "implies", "left": left, "right": right}


def make_iff(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "iff", "left": left, "right": right}


def make_forall(var: str, body: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "forall", "var": var, "body": body}


def make_exists(var: str, body: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "exists", "var": var, "body": body}


def make_predicate(name: str, args: List[str]) -> Dict[str, Any]:
    return {"type": "Predicate", "name": name, "args": args}


def make_true() -> Dict[str, Any]:
    return {"type": "true"}


def make_false() -> Dict[str, Any]:
    return {"type": "false"}


# === Type Checkers ===

def is_predicate(node: Dict[str, Any]) -> bool:
    return node.get("type") == "Predicate" and "name" in node and "args" in node


def is_variable(node: Dict[str, Any]) -> bool:
    return node.get("type") == "variable"


def is_quantifier(node: Dict[str, Any]) -> bool:
    return node.get("type") in {"forall", "exists"}


def is_logical_operator(node: Dict[str, Any]) -> bool:
    return node.get("type") in {"and", "or", "not", "implies", "iff"}


def is_terminal(node: Dict[str, Any]) -> bool:
    return node.get("type") in {"true", "false", "symbol", "variable"}


# === Traversal ===

def traverse_ast(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Recursively traverse the AST and return a flat list of all subnodes.
    """
    nodes = [node]
    node_type = node.get("type")

    if node_type in {"and", "or", "implies", "iff"}:
        nodes += traverse_ast(node.get("left"))
        nodes += traverse_ast(node.get("right"))
    elif node_type == "not":
        nodes += traverse_ast(node.get("value"))
    elif node_type in {"forall", "exists"}:
        nodes += traverse_ast(node.get("body"))
    elif node_type == "call":
        for arg in node.get("args", []):
            nodes += traverse_ast(arg)

    return nodes