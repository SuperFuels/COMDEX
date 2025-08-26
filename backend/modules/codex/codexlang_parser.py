import re
from typing import Union, List, Dict, Any
from backend.modules.symbolic.codex_ast_types import CodexAST

def tokenize_codexlang(expr: str) -> List[str]:
    # Basic tokenization for logic expressions
    tokens = re.findall(r"\w+|[\(\)\.,=\u2200\u2203\u2192\u2227\u2228\u00ac]", expr)
    return tokens


def parse_expression(tokens: List[str]) -> Any:
    def parse_term(index):
        token = tokens[index]

        if token == "∀":  # ∀ = ∀
            var = tokens[index + 1]
            assert tokens[index + 2] == "."
            body, next_index = parse_term(index + 3)
            return {"type": "forall", "var": var, "body": body}, next_index

        elif token == "∃":  # ∃ = ∃
            var = tokens[index + 1]
            assert tokens[index + 2] == "."
            body, next_index = parse_term(index + 3)
            return {"type": "exists", "var": var, "body": body}, next_index

        elif token == "¬":  # ¬ = ¬
            inner, next_index = parse_term(index + 1)
            return {"type": "not", "term": inner}, next_index

        elif token == "(" or re.match(r"\w+", token):
            # Could be predicate/function or simple var
            if index + 1 < len(tokens) and tokens[index + 1] == "(":
                name = token
                i = index + 2
                args = []
                while i < len(tokens) and tokens[i] != ")":
                    arg, i = parse_term(i)
                    args.append(arg if isinstance(arg, str) else arg.get("name", "?"))
                    if tokens[i] == ",":
                        i += 1
                assert tokens[i] == ")"
                return {"type": "function", "name": name, "args": args}, i + 1
            else:
                return token, index + 1

        return token, index + 1

    def parse_binary_ops(start_index):
        left, index = parse_term(start_index)

        while index < len(tokens):
            if tokens[index] == "→":  # → = →
                right, next_index = parse_term(index + 1)
                left = {"type": "implies", "left": left, "right": right}
                index = next_index
            elif tokens[index] == "∧":  # ∧ = ∧
                right, next_index = parse_term(index + 1)
                left = {"type": "and", "terms": [left, right]}
                index = next_index
            elif tokens[index] == "∨":  # ∨ = ∨
                right, next_index = parse_term(index + 1)
                left = {"type": "or", "terms": [left, right]}
                index = next_index
            elif tokens[index] == "=":
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
    Supports: ∀x. P(x) → Q(x), ∃y. P(y) ∧ Q(y), etc.
    """
    tokens = tokenize_codexlang(expr)
    if not tokens:
        return {"type": "empty"}
    return parse_expression(tokens)

def parse_codexlang(code: str) -> CodexAST:
    """
    Parse a CodexLang string like 'greater_than(x, y)' into a CodexAST.
    """
    try:
        if '(' not in code or ')' not in code:
            raise ValueError("CodexLang must contain parentheses: e.g., 'add(x, y)'")

        fn = code.split('(', 1)[0].strip()
        args = code.split('(', 1)[1].rsplit(')', 1)[0].split(',')
        args = [a.strip() for a in args if a.strip()]
        return CodexAST({"root": fn, "args": args})

    except Exception as e:
        raise ValueError(f"Invalid input for CodexLang parsing: {code}") from e


# Example:
# parse_codexlang_to_ast("\u2200x. P(x) → Q(x)")