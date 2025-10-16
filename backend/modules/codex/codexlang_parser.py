# File: backend/modules/codex/codexlang_parser.py
import os
import logging
import json
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from sentence_transformers import SentenceTransformer, util
import torch

from backend.modules.dna_chain.switchboard import DNA_SWITCH
from backend.config import GLYPH_API_BASE_URL
from backend.modules.dna_chain.container_index_writer import add_to_index  # ✅ R1f, ⏱️ H1

DNA_SWITCH.register(__file__)

MEMORY_DIR = "data/memory_logs"
ENABLE_GLYPH_LOGGING = True
AION_ENABLE = os.getenv("AION_ENABLE", "0") == "1"
AION_URL = os.getenv("AION_URL", GLYPH_API_BASE_URL or "http://localhost:8000")

MILESTONE_KEYWORDS = {
    "first_dream": ["dream_reflection"],
    "cognitive_reflection": ["self-awareness", "introspection", "echoes of existence"],
    "voice_activation": ["speak", "vocal", "communication interface"],
    "wallet_integration": ["wallet", "crypto storage", "store of value"],
    "nova_connection": ["frontend", "interface", "nova"],
}


class MemoryEngine:
    def __init__(self, container_id: str = "global"):
        self.container_id = container_id
        self.memory = []
        self.embeddings = []
        self.model = SentenceTransformer("./models/all-MiniLM-L6-v2", local_files_only=True)
        self.agents = []
        self.duplicate_threshold = 0.95

        self.memory_file = Path(__file__).parent / f"memory_{self.container_id}.json"
        self.embedding_file = Path(__file__).parent / f"embeddings_{self.container_id}.json"
        self.hashes_file = Path(__file__).parent / f"memhashes_{self.container_id}.json"

        self.dedupe_mode = os.getenv("MEMORY_DEDUPE_MODE", "exact")  # "exact" or "semantic"
        self._hashes = set()
        try:
            if self.hashes_file.exists():
                self._hashes = set(json.load(open(self.hashes_file)))
        except Exception:
            self._hashes = set()

        # 🧠 Memory filtering + sampling controls
        self.drop_labels = {"glyph_tick"}
        self.sample_labels = {"glyph_tick": 10}
        self._label_counts = defaultdict(int)
        # Optional quieter operation
        self.drop_labels.update({"codex_runtime_result"})
        self.sample_labels.update({
            "codex_trace:executed": 5,
            "runtime_tick_summary": 3,
        })

        # ✅ Lazy import pattern to break circular imports
        self.kg_writer = None

        self.load_memory()
        self.load_embeddings()

    def _get_kg_writer(self):
        """Lazy import to avoid circular dependency during boot."""
        if self.kg_writer is None:
            try:
                from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
                self.kg_writer = get_kg_writer()
            except Exception:
                self.kg_writer = None
        return self.kg_writer

    def detect_tags(self, content: str):
        tags = []
        content_lower = content.lower()
        if len(content_lower) < 30:
            return tags
        for tag, keywords in MILESTONE_KEYWORDS.items():
            if any(keyword.lower() in content_lower for keyword in keywords):
                tags.append(tag)
        return tags

    def is_duplicate(self, new_embedding):
        """Cosine-similarity deduplication with shape guards."""
        if not self.embeddings:
            return False

        try:
            if isinstance(new_embedding, torch.Tensor):
                ne = new_embedding.detach().to(torch.float32)
            else:
                ne = torch.tensor(new_embedding, dtype=torch.float32)
            if ne.ndim == 1:
                ne = ne.unsqueeze(0)
        except Exception:
            return False

        try:
            if isinstance(self.embeddings, list):
                emb_list = []
                for e in self.embeddings:
                    if isinstance(e, torch.Tensor):
                        emb_list.append(e.detach().to(torch.float32))
                    else:
                        emb_list.append(torch.tensor(e, dtype=torch.float32))
                if not emb_list:
                    return False
                E = torch.stack(emb_list, dim=0)
            else:
                E = torch.tensor(self.embeddings, dtype=torch.float32)
            if E.ndim == 1:
                E = E.unsqueeze(0)
        except Exception:
            return False

        if ne.shape[-1] != E.shape[-1]:
            return False

        try:
            sims = util.cos_sim(ne, E)[0]
            max_sim = float(sims.max()) if sims.numel() else 0.0
            return max_sim >= self.duplicate_threshold
        except Exception:
            return False

    @staticmethod
    def get_runtime_entropy_snapshot():
        return f"MemoryCount:{len(MEMORY.memory)};Timestamp:{datetime.utcnow().isoformat()}"

    def list_labels(self):
        return sorted(set(m.get("label") for m in self.memory if "label" in m))

    def get(self, label):
        return [m for m in self.memory if m.get("label") == label]

    def get_all(self):
        return self.memory

    def load_memory(self):
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r") as f:
                    self.memory = json.load(f)
            except Exception:
                self.memory = []
        else:
            self.memory = []

    def load_embeddings(self):
        if self.embedding_file.exists():
            try:
                with open(self.embedding_file, "r") as f:
                    loaded = json.load(f)
                    self.embeddings = [torch.tensor(e, dtype=torch.float32) for e in loaded]
            except Exception:
                self.embeddings = []
        else:
            self.embeddings = []

    def save_memory(self):
        try:
            with open(self.memory_file, "w") as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save memory file: {e}")

    def save_embeddings(self):
        try:
            with open(self.embedding_file, "w") as f:
                json.dump([e.tolist() for e in self.embeddings], f)
        except Exception as e:
            print(f"⚠️ Failed to save embeddings file: {e}")

    def register_agent(self, agent):
        if agent not in self.agents:
            self.agents.append(agent)
            print(f"✅ Agent registered: {agent.name}")

    def send_message_to_agents(self, message):
        for agent in self.agents:
            agent.receive_message(message)

    def save(self, label: str, content: str):
        self._store_impl({"label": label, "content": content})

    def _store_impl(self, memory_obj):
        """Core memory persistence logic with sampling and deduplication."""
        if not isinstance(memory_obj, dict):
            raise ValueError("Memory object must be a dict.")
        if "label" not in memory_obj or "content" not in memory_obj:
            raise ValueError("Memory must contain 'label' and 'content' keys.")

        content = memory_obj["content"]
        label = memory_obj["label"]

        # 🔻 Drop label entirely
        if label in self.drop_labels:
            return

        # 🎯 Sample noisy labels
        if label in self.sample_labels:
            self._label_counts[label] += 1
            if self._label_counts[label] % self.sample_labels[label] != 0:
                return

        # 🔒 Ensure string
        if not isinstance(content, str):
            try:
                content = json.dumps(content, ensure_ascii=False)
            except Exception:
                content = str(content)
        memory_obj["content"] = content

        # Embed and dedupe
        embedding = self.model.encode(content, convert_to_tensor=True)
        embedding = embedding.to(torch.float32)
        if self.is_duplicate(embedding):
            print(f"⚠️ Duplicate memory ignored: {label}")
            return

        memory_obj["timestamp"] = datetime.now().isoformat()
        tags = self.detect_tags(content)
        if tags:
            memory_obj["milestone_tags"] = tags

        # ✅ Attach scroll if glyph available
        glyph_payload = memory_obj.get("glyph") or memory_obj.get("glyph_tree")
        if glyph_payload:
            try:
                from backend.modules.codex.codex_scroll_builder import build_scroll_from_glyph

                # Guard: skip malformed glyphs (e.g., strings or empty dicts)
                if isinstance(glyph_payload, str) or not hasattr(glyph_payload, "__iter__"):
                    print("⚠️ Skipping scroll build: glyph_payload not structured")
                else:
                    scroll_data = build_scroll_from_glyph(glyph_payload)
                    if isinstance(scroll_data, dict):
                        memory_obj["scroll_preview"] = scroll_data.get("codexlang")
                        memory_obj["scroll_tree"] = scroll_data.get("tree")
                        print("🌀 Attached scroll to memory entry.")
            except Exception as e:
                print(f"⚠️ Failed to build scroll from glyph: {e}")

        self.memory.append(memory_obj)
        self.embeddings.append(embedding)
        self.save_memory()
        self.save_embeddings()
        print(f"✅ Memory stored: {label}")

        # 🧬 Synthesizing glyphs (AION optional)
        if AION_ENABLE:
            try:
                synth_response = requests.post(
                    f"{AION_URL}/api/aion/synthesize-glyphs",
                    json={"text": content, "source": "memory"},
                    timeout=3,  # shorter
                )
                if synth_response.ok:
                    result = synth_response.json()
                    count = len(result.get("glyphs", []))
                    print(f"✅ Synthesized {count} glyphs from memory via AION.")
                else:
                    print(f"⚠️ Glyph synthesis HTTP error: {synth_response.status_code}")
            except requests.exceptions.ConnectionError:
                print("🕳️ AION offline — skipping synthesis.")
            except Exception as e:
                print(f"⚠️ AION synth exception: {e}")

        # ✅ Inject glyph into knowledge graph + index
        if ENABLE_GLYPH_LOGGING:
            try:
                writer = self._get_kg_writer()
                if writer:
                    writer.inject_glyph(
                        content=content,
                        glyph_type="memory",
                        metadata={
                            "label": label,
                            "timestamp": memory_obj["timestamp"],
                            "tags": tags,
                            "container": self.container_id,
                        },
                        plugin="MemoryEngine",
                    )
                    print(f"🧠 Glyph injected into container for {label}")
                    add_to_index("memory_index.glyph", {
                        "text": content,
                        "timestamp": memory_obj["timestamp"],
                        "hash": hash(content),
                    })
            except Exception as e:
                print(f"⚠️ Glyph injection failed: {e}")


# 🧠 Global memory instance and helpers
_GLOBAL_MEMORY = MemoryEngine()
MEMORY = _GLOBAL_MEMORY
store_memory = MEMORY._store_impl


class MemoryBridge:
    @staticmethod
    def store_entry(entry: dict):
        MEMORY._store_impl(entry)

    @staticmethod
    def log_codex_execution(glyph: str, result: str, context: dict):
        MEMORY._store_impl({
            "label": "codex_execution",
            "type": "execution",
            "glyph": glyph,
            "result": result,
            "context": context,
        })


def get_recent_memory_glyphs(limit: int = 10) -> list[str]:
    try:
        if hasattr(MEMORY, "get_recent"):
            return [e.get("glyph") for e in MEMORY.get_recent(limit=limit) if e.get("glyph")]
        if hasattr(MEMORY, "log"):
            recent = list(MEMORY.log)[-limit:]
            return [e.get("glyph") for e in recent if e.get("glyph")]
    except Exception as e:
        print(f"⚠️ Failed to retrieve recent memory glyphs: {e}")
    return []

# File: backend/modules/codex/codexlang_parser.py
import re
import ast
from typing import List, Dict, Any
from backend.modules.symbolic.codex_ast_types import CodexAST

# ✅ TOKENIZER — required by symbolic.codex_ast_parser
def tokenize_codexlang(expr: str) -> List[str]:
    """
    Tokenize CodexLang logical expressions into symbols/operators.
    Supports operators like ∀, ∃, ¬, →, ↔, ⊕, ↑, ↓, ∈, =, etc.
    """
    token_pattern = r"(∀|∃|¬|→|↔|⊕|↑|↓|∈|=|[A-Za-z_]\w*|\(|\)|\.|,)"
    return re.findall(token_pattern, expr)

# ✅ PARSER — required by symbolic.codex_ast_parser
def parse_expression(tokens: List[str]) -> Any:
    """
    Parse a list of CodexLang tokens into an AST-like dictionary structure.
    Supports: ∀, ∃, ¬, →, ↔, ∧, ∨, ⊕, ↑, ↓, =, predicates/functions.

    Adds:
      - Defensive parsing for malformed tokens.
      - Graceful fallback for incomplete binary ops.
      - SoulLaw compliance stubs (type="empty" / type="error").
    """
    import logging

    if not tokens:
        logging.warning("[CodexLang] Empty token stream; returning empty node.")
        return {"type": "empty", "tokens": []}

    def parse_term(index: int):
        """Parse individual symbol, function, or negation."""
        if index >= len(tokens):
            return {"type": "empty"}, index

        token = tokens[index]

        # Handle negation ¬
        if token == "¬":
            inner, next_index = parse_term(index + 1)
            return {"type": "not", "term": inner}, next_index

        # Handle symbol or function call
        elif re.match(r"\w+", token):
            # Function or predicate with arguments
            if index + 1 < len(tokens) and tokens[index + 1] == "(":
                name = token
                args = []
                i = index + 2
                while i < len(tokens) and tokens[i] != ")":
                    arg, i = parse_term(i)
                    args.append(arg)
                    if i < len(tokens) and tokens[i] == ",":
                        i += 1
                if i >= len(tokens) or tokens[i] != ")":
                    logging.warning(f"[CodexLang] Unclosed '(' for function '{name}'")
                    return {"type": "function", "name": name, "args": args, "error": "unclosed_parenthesis"}, i
                return {"type": "function", "name": name, "args": args}, i + 1

            # Basic symbol
            return {"type": "symbol", "value": token}, index + 1

        # Fallback catch-all
        return {"type": "symbol", "value": token}, index + 1

    def parse_binary_ops(start_index: int):
        """Parse chained binary operations like A → B ↔ C."""
        left, index = parse_term(start_index)
        while index < len(tokens):
            op = tokens[index]
            if op in ("→", "↔", "∧", "∨", "⊕", "↑", "↓", "="):
                # Guard for incomplete or malformed RHS
                if index + 1 >= len(tokens):
                    logging.warning(f"[CodexLang] Missing right-hand operand after operator '{op}'")
                    return {"type": "error", "op": op, "left": left, "message": "missing_rhs"}, index + 1
                right, next_index = parse_term(index + 1)
                left = {"type": op, "left": left, "right": right}
                index = next_index
            else:
                break
        return left, index

    try:
        tree, _ = parse_binary_ops(0)
        if not isinstance(tree, dict):
            raise ValueError("Parse result not a dict")
        return tree
    except Exception as e:
        logging.warning(f"[CodexLang] Parse failure: {e} | Tokens={tokens}")
        return {
            "type": "error",
            "message": str(e),
            "tokens": tokens,
            "soul_state": "violated"
        }

def log_memory(container_id: str, data: dict):
    mem = MemoryEngine(container_id)
    mem._store_impl(data)


def get_runtime_entropy_snapshot():
    return MemoryEngine.get_runtime_entropy_snapshot()
    
def parse_codexlang_string(code_str):
    """
    Converts a symbolic CodexLang string like:
    ⟦ Logic | If: x > 5 → ⊕(Grow, Reflect) ⟧
    into a structured AST-like dictionary with canonicalized ops.

    ✅ SoulLaw-compliant: gracefully handles partial or malformed glyphs.
    🧩 Enhanced with DEBUG instrumentation to trace unpack errors and caller context.
    """
    import inspect
    import traceback

    try:
        caller = inspect.stack()[1]
        print("\n[🧠 DEBUG] parse_codexlang_string CALLED")
        print(f"   📍 Caller: {caller.filename}:{caller.lineno} → {caller.function}")
        print(f"   🧩 Raw code_str: {repr((code_str or '')[:100])}")

        body = (code_str or "").strip("⟦⟧ ").strip()
        if not body:
            print("   ⚠️ Empty CodexLang body")
            return {"type": "empty", "soul_state": "violated", "message": "Empty glyph string"}

        # 🧩 Case 1 — shorthand (no →)
        if "→" not in body:
            if ":" not in body or "|" not in body:
                print("   ⚠️ Missing ':' or '|' in shorthand CodexLang")
                return {
                    "type": "incomplete",
                    "expr": body,
                    "soul_state": "partial",
                    "message": "Missing ':' or '|' structure in CodexLang string",
                }

            try:
                type_tag, action = body.split(":", 1)
                g_type, tag = type_tag.split("|", 1)
            except ValueError as ve:
                print(f"   ⚠️ ValueError in shorthand split: {ve}")
                return {
                    "type": "incomplete",
                    "expr": body,
                    "soul_state": "partial",
                    "message": "Malformed type/tag section"
                }

            parsed_action = parse_action_expr(action.strip())
            parsed_action = translate_node(parsed_action, context=g_type.strip().lower())
            parsed = {
                "type": g_type.strip().lower(),
                "tag": tag.strip(),
                "value": None,
                "action": parsed_action,
                "soul_state": "trusted",
            }
            print("   ✅ Parsed shorthand CodexLang successfully.")
            return parsed

        # 🧩 Case 2 — full form with →
        parts = body.split("→", 1)
        print(f"   🔍 parts after split('→',1): {len(parts)} parts")
        if len(parts) != 2:
            print("   ⚠️ Detected malformed CodexLang (missing RHS after →)")
            return {
                "type": "incomplete",
                "expr": body,
                "soul_state": "partial",
                "message": "Missing right-hand operand after '→'",
            }

        left, action = parts
        if ":" not in left or "|" not in left:
            print("   ⚠️ Missing ':' or '|' in left-hand side")
            return {
                "type": "incomplete",
                "expr": body,
                "soul_state": "partial",
                "message": "Missing ':' or '|' in left-hand side",
            }

        try:
            type_tag, value = left.split(":", 1)
            g_type, tag = type_tag.split("|", 1)
        except ValueError as ve:
            print(f"   ⚠️ ValueError in left-hand split: {ve}")
            return {
                "type": "incomplete",
                "expr": body,
                "soul_state": "partial",
                "message": "Malformed left-hand type/tag/value section"
            }

        parsed_action = parse_action_expr(action.strip())
        parsed_action = translate_node(parsed_action, context=g_type.strip().lower())

        parsed = {
            "type": g_type.strip().lower(),
            "tag": tag.strip(),
            "value": value.strip(),
            "action": parsed_action,
            "soul_state": "trusted",
        }

        if parsed["type"] == "logic":
            parsed["tree"] = translate_node(logic_to_tree(action.strip()), context="logic")

        print(f"   ✅ Parsed full CodexLang successfully. Type={parsed['type']}, Tag={parsed['tag']}")
        return parsed

    except Exception as e:
        # Helpful debug output when parse fails (shows raw input + stack)
        print(f"[⚠️ parse_codexlang_string] Exception: {e}")
        print(f"   🔍 Raw input was: {repr(code_str)}")
        import traceback
        traceback.print_exc()

        return {
            "type": "error",
            "soul_state": "violated",
            "expr": code_str,
            "message": str(e)
        }