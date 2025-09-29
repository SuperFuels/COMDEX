# -*- coding: utf-8 -*-
# File: backend/core/registry_bridge.py
"""
Registry Bridge
---------------

Unifies:
  • symbol_registry (static symbol tables)
  • instruction_registry (runtime handlers)
  • symbolic_registry (glyph tree/object store)
  • codex_instruction_set.yaml (YAML-defined ops)
  • glyph_instruction_set (runtime glyph ops)

Ensures:
  - Every symbol in symbol_registry has a runtime handler (or explicit stub).
  - YAML + Glyph ops are auto-registered.
  - Symatics ops are bound to rulebook handlers.
  - Executors call through a single resolve_and_execute() API.
"""
import json
import time
import warnings
from typing import Any, Dict
from pathlib import Path
import yaml
from backend.core.log_utils import make_log_event, log_event
from backend.core import symbol_registry
from backend.codexcore_virtual import instruction_registry
from backend.modules.codex.symbolic_registry import symbolic_registry
from backend.symatics import symatics_rulebook as SR
from backend.modules.glyphos import glyph_instruction_set as GIS


# ------------------------------------------------------------------
# Loader for YAML codex instruction set
# ------------------------------------------------------------------
def _load_codex_instruction_set():
    # Look inside glyphos submodule
    path = Path(__file__).resolve().parent.parent / "modules" / "glyphos" / "codex_instruction_set.yaml"

    if not path.exists():
        warnings.warn(f"[CodexLoader] Instruction set YAML not found at {path}", RuntimeWarning)
        return {}

    with open(path, "r", encoding="utf-8") as f:
        ops = yaml.safe_load(f) or {}
        print(f"[DEBUG] Loaded {len(ops)} codex ops from YAML")
        return ops


class RegistryBridge:
    def __init__(self):
        self.symbol_registry = symbol_registry.REGISTRY
        self.instruction_registry = instruction_registry.registry
        self.symbolic_registry = symbolic_registry

    # ------------------------------------------------------------------
    # Resolution Helpers
    # ------------------------------------------------------------------
    def resolve_symbol(self, symbol: str) -> Dict[str, str]:
        """Return meaning across domains for a symbol."""
        return symbol_registry.lookup_symbol(symbol)

    def _canonicalize(self, symbol: str) -> str:
        """Map raw symbol → canonical domain:key if alias exists."""
        if symbol in self.instruction_registry.registry:
            return symbol
        if symbol in self.instruction_registry.aliases:
            return self.instruction_registry.aliases[symbol]
        return symbol

    def has_handler(self, symbol: str) -> bool:
        """Check if runtime has a handler for symbol or alias."""
        canonical = self._canonicalize(symbol)
        return canonical in self.instruction_registry.registry

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def resolve_and_execute(self, op: str, *args, **kwargs) -> Any:
        canonical = self._canonicalize(op)

        if canonical not in self.instruction_registry.registry:
            event = make_log_event(
                event="registry_execute",
                op=op,
                canonical=canonical,
                args=args,
                kwargs={k: v for k, v in kwargs.items() if k != "ctx"},
                status="stub",
                result=None,
                error=f"No handler for {op}",
            )
            log_event(event)
            return {"unhandled_op": op, "args": args, "kwargs": kwargs}

        try:
            result = self.instruction_registry.execute_v2(canonical, *args, **kwargs)
            event = make_log_event(
                event="registry_execute",
                op=op,
                canonical=canonical,
                args=args,
                kwargs={k: v for k, v in kwargs.items() if k != "ctx"},
                status="ok",
                result=result,
                error=None,
            )
            log_event(event)
            return result
        except Exception as e:
            event = make_log_event(
                event="registry_execute",
                op=op,
                canonical=canonical,
                args=args,
                kwargs={k: v for k, v in kwargs.items() if k != "ctx"},
                status="error",
                result=None,
                error=str(e),
            )
            log_event(event)
            raise

    # ------------------------------------------------------------------
    # Synchronization
    # ------------------------------------------------------------------
    def sync_from_symbol_registry(self) -> None:
        """
        Ensure all symbols from:
        • symbol_registry
        • codex_instruction_set.yaml
        • glyph_instruction_set
        exist in instruction_registry.
        Missing ones get stub handlers.
        """

        # --- Core symbol_registry domains ---
        def _make_stub(domain, sym, meaning):
            def _stub(ctx, *args, **kwargs):
                warnings.warn(
                    f"[Stub] {domain}:{sym} not implemented. Meaning={meaning}",
                    RuntimeWarning,
                )
                return {"stub": sym, "domain": domain, "args": args, "kwargs": kwargs}
            return _stub

        for domain, table in self.symbol_registry.items():
            for sym, meaning in table.items():
                if not self.has_handler(sym):
                    key = f"{domain}:{sym}" if not sym.startswith(f"{domain}:") else sym
                    try:
                        self.instruction_registry.register(key, _make_stub(domain, sym, meaning))
                        self.instruction_registry.alias(sym, key)
                    except ValueError:
                        pass

        # --- YAML codex ops ---
        def _make_codex_wrap(fn_name, sym):
            def _wrap(ctx, *args, **kwargs):
                try:
                    mod = __import__(
                        "backend.modules.codex.ops." + fn_name,
                        fromlist=[fn_name],
                    )
                    fn = getattr(mod, fn_name)
                    return fn(*args, **kwargs)
                except Exception as e:
                    warnings.warn(f"[Stub] Failed {sym} → {fn_name}: {e}", RuntimeWarning)
                    return {"stub": sym, "error": str(e)}
            return _wrap

        codex_ops = _load_codex_instruction_set()
        codex_ops = _load_codex_instruction_set()
        print(f"[DEBUG] Loaded {len(codex_ops)} codex ops from YAML")      
        for sym, meta in codex_ops.items():
            canonical = f"{meta.get('category', 'core')}:{sym}"
            if not self.has_handler(canonical):
                fn_name = meta["function"]
                try:
                    self.instruction_registry.register(canonical, _make_codex_wrap(fn_name, sym))
                    self.instruction_registry.alias(sym, canonical)
                    print(f"[DEBUG] Registering Codex op {sym} as {canonical} → {fn_name}")
                except ValueError:
                    pass

        # --- GlyphInstructionSet ops ---
        def _make_glyph_wrap(instr):
            def _wrap(ctx, *args, **kwargs):
                return instr.execute(*args, **kwargs)
            return _wrap

        for sym, instr in GIS.INSTRUCTION_SET.items():
            canonical = f"glyph:{sym}"
            if not self.has_handler(canonical):
                try:
                    self.instruction_registry.register(canonical, _make_glyph_wrap(instr))
                    self.instruction_registry.alias(sym, canonical)
                except ValueError:
                    pass

    # ------------------------------------------------------------------
    # Extra Sync — Symatics Ops
    # ------------------------------------------------------------------
    def sync_symatics_ops(self) -> None:
        """Ensure Symatics ops are bound into the registry."""
        def _reg(symbol: str, handler, domain="symatics"):
            key = f"{domain}:{symbol}"
            try:
                self.instruction_registry.register(key, handler)
                self.instruction_registry.alias(symbol, key)
            except ValueError:
                pass

        _reg("⊕", SR.op_superpose)
        _reg("μ", lambda ctx, expr=None, context=None, **kw: SR.op_measure(SR.collapse_rule(expr), context or {}))
        _reg("↔", SR.op_entangle)
        _reg("⟲", SR.op_recurse)
        _reg("π", SR.op_project)

    # ------------------------------------------------------------------
    # Symbolic Registry Integration
    # ------------------------------------------------------------------
    def store_symbolic(self, name: str, obj: Any) -> None:
        """Store a symbolic tree in the global symbolic registry."""
        self.symbolic_registry.register(name, obj)

    def fetch_symbolic(self, name: str) -> Any:
        """Fetch from global symbolic registry."""
        return self.symbolic_registry.get(name)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def resolve_and_execute(self, op: str, *args, **kwargs) -> Any:
        """
        Resolve symbol → canonical key → execute handler.
        Falls back to stub if not implemented.
        Adds C13 structured logging.
        """
        canonical = self._canonicalize(op)

        log_event = {
            "event": "registry_execute",
            "timestamp": time.time(),
            "op": op,
            "canonical": canonical,
            "args": args,
            "kwargs": {k: v for k, v in kwargs.items() if k != "ctx"},  # omit ctx for clarity
        }

        if canonical not in self.instruction_registry.registry:
            warnings.warn(f"[RegistryBridge] No handler for '{op}'. Using stub.", RuntimeWarning)
            log_event["status"] = "stub"
            print("[LOG]", json.dumps(log_event, ensure_ascii=False))
            return {"unhandled_op": op, "args": args, "kwargs": kwargs}

        try:
            result = self.instruction_registry.execute_v2(canonical, *args, **kwargs)
            log_event["status"] = "ok"
            log_event["result"] = result
            print("[LOG]", json.dumps(log_event, ensure_ascii=False))
            return result
        except Exception as e:
            log_event["status"] = "error"
            log_event["error"] = str(e)
            print("[LOG]", json.dumps(log_event, ensure_ascii=False))
            raise


# ✅ Singleton bridge
registry_bridge = RegistryBridge()
registry_bridge.sync_from_symbol_registry()
registry_bridge.sync_symatics_ops()