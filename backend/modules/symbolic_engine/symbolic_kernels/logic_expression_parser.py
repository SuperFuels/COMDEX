# backend/modules/symbolic_engine/symbolic_kernels/logic_expression_parser.py

import re
from typing import List, Union
from .logic_glyphs import (
    LogicGlyph, AndGlyph, OrGlyph, NotGlyph, ImplicationGlyph,
    ProvableGlyph, EntailmentGlyph, TrueGlyph, FalseGlyph, SymbolGlyph
)

class Token:
    def __init__(self, type_: str, value: str):
        self.type = type_
        self.value = value
    def __repr__(self):
        return f"{self.type}({self.value})"

# Token types
TOKEN_REGEX = [
    ('TURNSTILE', r'⊢'),
    ('ENTAILS', r'⊨'),
    ('TOP', r'⊤'),
    ('BOTTOM', r'⊥'),
    ('LPAREN', r'\('),
    ('RPAREN', r'\)'),
    ('IMPLIES', r'->'),
    ('AND', r'∧'),
    ('OR', r'∨'),
    ('NOT', r'¬'),
    ('SYMBOL', r'[A-Za-z0-9_]+'),
]

def tokenize(expr: str) -> List[Token]:
    expr = expr.replace(" ", "")
    pattern = '|'.join(f'(?P<{name}>{regex})' for name, regex in TOKEN_REGEX)
    tokens = []
    for match in re.finditer(pattern, expr):
        kind = match.lastgroup
        value = match.group()
        tokens.append(Token(kind, value))
    return tokens

# Recursive descent parser
class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Union[Token, None]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, expected_type=None) -> Token:
        token = self.peek()
        if not token:
            raise ValueError("Unexpected end of input.")
        if expected_type and token.type != expected_type:
            raise ValueError(f"Expected {expected_type}, got {token.type}")
        self.pos += 1
        return token

    def parse_expression(self) -> LogicGlyph:
        token = self.peek()
        if token and token.type in ('TURNSTILE', 'ENTAILS'):
            prefix = self.consume().type
            inner = self.parse_implication()
            if prefix == 'TURNSTILE':
                return ProvableGlyph([], inner)
            elif prefix == 'ENTAILS':
                return EntailmentGlyph([], inner)
        return self.parse_implication()

    def parse_implication(self) -> LogicGlyph:
        left = self.parse_or()
        while self.peek() and self.peek().type == 'IMPLIES':
            self.consume('IMPLIES')
            right = self.parse_or()
            left = ImplicationGlyph(left, right)
        return left

    def parse_or(self) -> LogicGlyph:
        left = self.parse_and()
        while self.peek() and self.peek().type == 'OR':
            self.consume('OR')
            right = self.parse_and()
            left = OrGlyph(left, right)
        return left

    def parse_and(self) -> LogicGlyph:
        left = self.parse_not()
        while self.peek() and self.peek().type == 'AND':
            self.consume('AND')
            right = self.parse_not()
            left = AndGlyph(left, right)
        return left

    def parse_not(self) -> LogicGlyph:
        if self.peek() and self.peek().type == 'NOT':
            self.consume('NOT')
            operand = self.parse_atom()
            return NotGlyph(operand)
        return self.parse_atom()

    def parse_atom(self) -> LogicGlyph:
        token = self.peek()
        if token.type == 'LPAREN':
            self.consume('LPAREN')
            expr = self.parse_expression()
            self.consume('RPAREN')
            return expr
        elif token.type == 'TOP':
            self.consume('TOP')
            return TrueGlyph()
        elif token.type == 'BOTTOM':
            self.consume('BOTTOM')
            return FalseGlyph()
        elif token.type == 'SYMBOL':
            value = self.consume('SYMBOL').value
            return SymbolGlyph(value)
        else:
            raise ValueError(f"Unexpected token {token}")

# Entry point
def parse_logic_expression(expression: str) -> LogicGlyph:
    tokens = tokenize(expression)
    parser = Parser(tokens)
    return parser.parse_expression()