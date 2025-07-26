import re
import hashlib
from typing import List, Dict, Optional
from backend.modules.hexcore.memory_engine import MEMORY
from backend.modules.codex.symbolic_key_deriver import SymbolicKeyDerivation
from backend.modules.glyphos.symbolic_entangler import get_entangled_links


class KeyFragmentResolver:
    def __init__(self, container_id: str = "global"):
        self.container_id = container_id
        self.memory = MEMORY.get_all() if container_id == "global" else self._load_memory()
        self.fragments: Dict[str, str] = {}
        self.recombined_key: Optional[str] = None

    def _load_memory(self) -> List[Dict]:
        from backend.modules.hexcore.memory_engine import MemoryEngine
        mem = MemoryEngine(self.container_id)
        return mem.get_all()

    def extract_key_fragments(self, key_id: str) -> List[str]:
        """
        Extract memory fragments labeled as split key pieces.
        Format: "↔key:<key_id>#<index>" in memory label or content
        """
        fragments = []
        pattern = re.compile(rf"↔key:{re.escape(key_id)}[#\-]?\d*", re.IGNORECASE)

        for entry in self.memory:
            label = entry.get("label", "")
            content = entry.get("content", "")
            if pattern.search(label) or pattern.search(content):
                frag = self._sanitize_fragment(content)
                if frag:
                    fragments.append(frag)

        return fragments

    def _sanitize_fragment(self, raw: str) -> Optional[str]:
        """
        Sanitize content fragment to extract usable key material.
        """
        lines = raw.splitlines()
        for line in lines:
            if "key_fragment" in line or "↔" in line or "🔑" in line:
                cleaned = line.strip().replace("🔑", "").replace("↔", "")
                return cleaned.split(":")[-1].strip()
        return None

    def recombine_key(self, key_id: str) -> Optional[str]:
        """
        Recombine all fragments into a single symbolic key string.
        Order is not guaranteed, so we concatenate all unique pieces.
        """
        fragments = self.extract_key_fragments(key_id)
        if not fragments:
            print(f"⚠️ No key fragments found for {key_id}")
            return None

        unique_parts = sorted(set(fragments))
        recombined = "::".join(unique_parts)
        print(f"✅ Recombined key [{key_id}]: {recombined}")
        self.recombined_key = recombined
        return recombined

    def verify_and_activate(self, key_id: str) -> bool:
        """
        Reconstruct the symbolic key and verify via entropy.
        """
        combined_key = self.recombine_key(key_id)
        if not combined_key:
            return False

        derivation = SymbolicKeyDerivation()
        is_valid = derivation.verify_key(key=combined_key, avatar_state="auto")

        if is_valid:
            print(f"🔓 Split key [{key_id}] verified and activated.")
            return True
        else:
            print(f"❌ Split key [{key_id}] failed verification.")
            return False

    # ────────────────────────────────────────────────
    # 🧠 New Methods: Entangled Key Fragments from .dc
    # ────────────────────────────────────────────────

    def load_fragments_from_dc(self, glyphs: List[Dict]) -> None:
        """
        Loads key fragments directly from glyphs in a .dc container.
        Assumes each glyph may have a 'key_fragment' field.
        """
        for glyph in glyphs:
            frag = glyph.get("key_fragment")
            gid = glyph.get("id")
            if frag and gid:
                self.fragments[gid] = frag
                print(f"📦 Found glyph key fragment: {gid} → {frag}")

    def resolve_entangled_order(self) -> List[str]:
        """
        Use the symbolic entanglement graph to determine deterministic glyph ordering.
        """
        entangled_links = get_entangled_links(self.container_id)
        ordered = []
        visited = set()

        def dfs(node):
            if node in visited:
                return
            visited.add(node)
            ordered.append(node)
            for neighbor in entangled_links.get(node, []):
                dfs(neighbor)

        for start in self.fragments.keys():
            dfs(start)

        return ordered

    def recombine_entangled_key(self) -> Optional[str]:
        """
        Combine key fragments from glyphs in entangled order using SHA-256.
        """
        ordered_ids = self.resolve_entangled_order()
        if not ordered_ids:
            print("⚠️ No entangled glyphs found.")
            return None

        combined = ""
        for gid in ordered_ids:
            frag = self.fragments.get(gid, "")
            combined += frag

        hashed = hashlib.sha256(combined.encode()).hexdigest()
        self.recombined_key = hashed
        print(f"🧬 Recombined entangled key: {hashed}")
        return hashed

    def inject_to_memory(self) -> None:
        """
        Store recombined entangled key in memory.
        """
        if not self.recombined_key:
            print("⚠️ No recombined key to inject.")
            return

        MEMORY.store({
            "label": f"key:recombined:{self.container_id}",
            "content": f"[🔐] Recombined symbolic key: {self.recombined_key}",
            "type": "symbolic_key"
        })
        print(f"🧠 Injected recombined key into memory for container {self.container_id}.")

    def run_entangled_recombination(self, glyphs: List[Dict]) -> Optional[str]:
        """
        Run the full entangled recombination from .dc glyphs.
        """
        self.load_fragments_from_dc(glyphs)
        self.recombine_entangled_key()
        self.inject_to_memory()
        return self.recombined_key