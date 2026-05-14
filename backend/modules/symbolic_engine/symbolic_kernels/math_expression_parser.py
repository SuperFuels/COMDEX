# backend/modules/symbolic_engine/symbolic_kernels/math_expression_parser.py

import re
from typing import List, Union
from .math_glyphs import (
    MathGlyph,
    AddGlyph, SubtractGlyph, MultiplyGlyph, DivideGlyph, PowerGlyph
)

Token = Union[str, float]

# -----------------------------
# Tokenizer
# -----------------------------

def tokenize(expr: str) -> List[Token]:
    tokens = re.findall(r'\d+\.\d+|\d+|[a-zA-Z_]+|[+\-*/^()]', expr)
    result = []
    for token in tokens:
        if token.isdigit() or re.match(r'\d+\.\d+', token):
            result.append(float(token) if '.' in token else int(token))
        else:
            result.append(token)
    return result


# -----------------------------
# Recursive Parser (Pratt-style)
# -----------------------------

class MathExpressionParser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Token:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self) -> Token:
        tok = self.peek()
        if tok is not None:
            self.pos += 1
        return tok

    def parse(self) -> MathGlyph:
        return self.parse_expression()

    def parse_expression(self, precedence=0) -> MathGlyph:
        left = self.parse_primary()

        while True:
            op = self.peek()
            if op not in OPERATORS or PRECEDENCE[op] < precedence:
                break
            self.consume()
            right = self.parse_expression(PRECEDENCE[op] + 1)
            left = self.apply_operator(op, left, right)

        return left

    def parse_primary(self) -> Union[MathGlyph, Token]:
        tok = self.consume()
        if isinstance(tok, (int, float)):
            return tok
        elif isinstance(tok, str):
            if tok == '(':
                expr = self.parse_expression()
                if self.consume() != ')':
                    raise ValueError("Expected closing parenthesis")
                return expr
            return tok  # variable name
        raise ValueError(f"Unexpected token: {tok}")

    def apply_operator(self, op: str, a: Union[MathGlyph, Token], b: Union[MathGlyph, Token]) -> MathGlyph:
        glyph_cls = OPERATOR_MAP.get(op)
        if not glyph_cls:
            raise ValueError(f"Unsupported operator: {op}")
        return glyph_cls(a, b)


# -----------------------------
# Public API
# -----------------------------

def parse_math_expression(expr: str) -> MathGlyph:
    tokens = tokenize(expr)
    parser = MathExpressionParser(tokens)
    return parser.parse()


# -----------------------------
# Operator Metadata
# -----------------------------

PRECEDENCE = {
    '+': 10,
    '-': 10,
    '*': 20,
    '/': 20,
    '^': 30,
}

OPERATORS = set(PRECEDENCE.keys())

OPERATOR_MAP = {
    '+': AddGlyph,
    '-': SubtractGlyph,
    '*': MultiplyGlyph,
    '/': DivideGlyph,
    '^': PowerGlyph,
}