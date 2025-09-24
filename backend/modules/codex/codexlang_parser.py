# File: backend/modules/codex/codexlang_parser.py

import re
import ast
from typing import List, Dict, Any
from backend.modules.symbolic.codex_ast_types import CodexAST


def parse_python_string_to_codex_ast(source: str) -> CodexAST:
    """Parse a single Python expression string into CodexAST."""
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            fn_name = node.value.func.id if isinstance(node.value.func, ast.Name) else "unknown"
            args = []
            for arg in node.value.args:
                if isinstance(arg, ast.Name):
                    args.append(arg.id)
                elif isinstance(arg, ast.Constant):
                    args.append(str(arg.value))
                else:
                    args.append("expr")

            return CodexAST({"root": fn_name, "args": args})

    raise ValueError("No valid function call found in source")


def parse_python_file_to_codex_ast(code: str) -> CodexAST:
    """
    Parse Python source code into CodexAST.
    Extracts top-level function calls and assignments.
    """
    try:
        tree = ast.parse(code)
        root_nodes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                fn = node.value.func
                fn_name = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", "unknown")
                args = []
                for arg in node.value.args:
                    if isinstance(arg, ast.Name):
                        args.append(arg.id)
                    elif isinstance(arg, ast.Constant):
                        args.append(str(arg.value))
                    elif isinstance(arg, ast.Attribute):
                        args.append(arg.attr)
                    else:
                        args.append("expr")
                root_nodes.append({"type": "call", "name": fn_name, "args": args})

            elif isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                value = node.value
                if isinstance(value, ast.Name):
                    val = value.id
                elif isinstance(value, ast.Constant):
                    val = str(value.value)
                else:
                    val = "expr"
                root_nodes.append({"type": "assign", "targets": targets, "value": val})

        return CodexAST({"root": "module", "args": root_nodes})

    except Exception as e:
        return CodexAST({"root": "error", "args": [str(e)]})


def tokenize_codexlang(expr: str) -> List[str]:
    """
    Tokenize CodexLang logical expressions into symbols/operators.
    """
    token_pattern = r"(∀|∃|¬|→|↔|⊕|↑|↓|∈|[A-Za-z_]\w*|\(|\)|\.|,)"
    return re.findall(token_pattern, expr)


def parse_expression(tokens: List[str]) -> Any:
    """
    Parse a list of CodexLang tokens into an AST structure.
    Supports: ∀, ∃, ¬, →, ↔, ∧, ∨, ⊕, ↑, ↓, =, predicates/functions.
    """

    def parse_term(index: int):
        token = tokens[index]

        # ∀x or ∀x ∈ S. ...
        if token == "∀":
            var = tokens[index + 1]

            if index + 4 < len(tokens) and tokens[index + 2] == "∈" and tokens[index + 4] == ".":
                domain = tokens[index + 3]
                body, next_index = parse_term(index + 5)
                domain_pred = {"type": "function", "name": domain, "args": [var]}
                implication = {"type": "implies", "left": domain_pred, "right": body}
                return {"type": "forall", "var": var, "body": implication}, next_index
            else:
                assert tokens[index + 2] == ".", f"Expected '.' in ∀x. form | Got: {tokens[index+2]}"
                body, next_index = parse_term(index + 3)
                return {"type": "forall", "var": var, "body": body}, next_index

        # ∃x. ...
        elif token == "∃":
            var = tokens[index + 1]
            assert tokens[index + 2] == ".", "Expected '.' in ∃x. form"
            body, next_index = parse_term(index + 3)
            return {"type": "exists", "var": var, "body": body}, next_index

        # ¬φ
        elif token == "¬":
            inner, next_index = parse_term(index + 1)
            return {"type": "not", "term": inner}, next_index

        # Function, predicate, or constant
        elif re.match(r"\w+", token):
            if index + 1 < len(tokens) and tokens[index + 1] == "(":
                name = token
                i = index + 2
                args = []
                while i < len(tokens) and tokens[i] != ")":
                    arg, i = parse_term(i)
                    args.append(arg)
                    if i < len(tokens) and tokens[i] == ",":
                        i += 1
                assert i < len(tokens) and tokens[i] == ")", f"Expected closing ')' in function call: {name}"
                return {"type": "function", "name": name, "args": args}, i + 1
            else:
                return {"type": "function", "name": token, "args": []}, index + 1

        # Fallback
        return {"type": "symbol", "value": token}, index + 1

    def parse_binary_ops(start_index: int):
        left, index = parse_term(start_index)

        while index < len(tokens):
            op = tokens[index]
            if op == "→":
                right, next_index = parse_term(index + 1)
                left = {"type": "implies", "left": left, "right": right}
                index = next_index
            elif op == "↔":
                right, next_index = parse_term(index + 1)
                left = {"type": "iff", "left": left, "right": right}
                index = next_index
            elif op == "∧":
                right, next_index = parse_term(index + 1)
                left = {"type": "and", "terms": [left, right]}
                index = next_index
            elif op == "∨":
                right, next_index = parse_term(index + 1)
                left = {"type": "or", "terms": [left, right]}
                index = next_index
            elif op == "⊕":
                right, next_index = parse_term(index + 1)
                left = {"type": "xor", "terms": [left, right]}
                index = next_index
            elif op == "↑":
                right, next_index = parse_term(index + 1)
                left = {"type": "nand", "terms": [left, right]}
                index = next_index
            elif op == "↓":
                right, next_index = parse_term(index + 1)
                left = {"type": "nor", "terms": [left, right]}
                index = next_index
            elif op == "=":
                right, next_index = parse_term(index + 1)
                left = {"type": "equals", "left": left, "right": right}
                index = next_index
            else:
                break

        return left, index

    tree, _ = parse_binary_ops(0)
    return tree


def parse_codexlang_to_ast(expr: str) -> Dict[str, Any]:
    """
    Parse a CodexLang logic expression into an AST.
    """
    tokens = tokenize_codexlang(expr)
    if not tokens:
        return {"type": "empty"}
    return parse_expression(tokens)


def parse_codexlang(code: str) -> CodexAST:
    """
    Parse a CodexLang string like 'greater_than(x, y)' into CodexAST.
    If input has no parentheses, treat as constant symbol.
    """
    try:
        if "(" not in code:
            return CodexAST({"root": code.strip(), "args": []})
        if ")" not in code:
            raise ValueError("CodexLang must contain matching parentheses")

        fn = code.split("(", 1)[0].strip()
        args = code.split("(", 1)[1].rsplit(")", 1)[0].split(",")
        args = [a.strip() for a in args if a.strip()]
        return CodexAST({"root": fn, "args": args})

    except Exception as e:
        raise ValueError(f"Invalid input for CodexLang parsing: {code}") from e


# Example:
# parse_codexlang_to_ast("∀x. P(x) → Q(x)")