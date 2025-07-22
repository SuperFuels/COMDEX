# File: backend/codexcore_virtual/instruction_set.py

from enum import Enum

class Opcode(str, Enum):
    LOAD = "LOAD"
    STORE = "STORE"
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    PUSH = "PUSH"
    POP = "POP"
    JMP = "JMP"
    JZ = "JZ"         # Jump if zero
    JNZ = "JNZ"       # Jump if not zero
    CALL = "CALL"
    RET = "RET"
    NOOP = "NOOP"
    HALT = "HALT"

    # Symbolic Opcodes
    SYMBOLIC_ADD = "⊕"
    SYMBOLIC_SEND = "→"
    SYMBOLIC_LOOP = "⟲"
    SYMBOLIC_LINK = "↔"
    SYMBOLIC_DELAY = "⧖"


# Human-readable descriptions
OPCODE_DOCS = {
    "LOAD": "Load value from memory to register",
    "STORE": "Store register value to memory",
    "ADD": "Add two values",
    "SUB": "Subtract two values",
    "MUL": "Multiply two values",
    "DIV": "Divide two values",
    "PUSH": "Push value to stack",
    "POP": "Pop value from stack",
    "JMP": "Jump to instruction address",
    "JZ": "Jump if accumulator is zero",
    "JNZ": "Jump if accumulator is not zero",
    "CALL": "Call subroutine",
    "RET": "Return from subroutine",
    "NOOP": "Do nothing",
    "HALT": "Stop execution",
    "⊕": "Symbolic merge or synthesis operation",
    "→": "Symbolic data transmission or intention",
    "⟲": "Symbolic loop or reflection",
    "↔": "Symbolic link or entanglement",
    "⧖": "Symbolic delay or cost computation",
}