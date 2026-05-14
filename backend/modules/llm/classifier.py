# ──────────────────────────────────────────────────────────────
#  Tessaris * AION LLM Classifier (v1.2 Quantum-Ready Hardened)
#  Semantic brainstem for AION - interprets intents via OpenAI or Quantum Atom.
#  Self-adapts to offline symbolic fallback when OpenAI is unavailable.
#  Hardened against unicode / dict / non-string payloads.
# ──────────────────────────────────────────────────────────────

from __future__ import annotations

import os
import asyncio
import logging
from typing import Any, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

from backend.modules.holograms.morphic_ledger import MorphicLedger

load_dotenv()

logger = logging.getLogger("LLMClassifier")


class LLMClassifier:
    """
    AION's semantic brainstem.
    Performs low-entropy classification of natural-language or symbolic input
    into intent tags used by the CognitiveDispatcher.
    """

    def __init__(self, model: Optional[str] = None, quantum_atom: Any = None):
        self.model = model or os.getenv("AION_LLM_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("AION_LLM_TEMP", "0.2"))
        self.quantum_atom = quantum_atom  # optional fallback
        self.history: list[dict[str, Any]] = []
        self.ledger = MorphicLedger()

        api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None

        if self.client:
            logger.info(f"✅ LLMClassifier initialized using model: {self.model}")
        else:
            logger.warning("⚠️ OpenAI client not configured - using symbolic fallback only.")

    # ──────────────────────────────────────────────────────────────
    def _normalize_text(self, text: Any) -> str:
        """
        Normalize arbitrary input into safe unicode text for classification.
        Prevents crashes from dict/list payloads, smart quotes, and odd objects.
        """
        try:
            if text is None:
                return ""

            if isinstance(text, str):
                normalized = text.strip()

            elif isinstance(text, dict):
                if "input" in text:
                    normalized = str(text.get("input", "")).strip()
                elif "signal" in text:
                    normalized = str(text.get("signal", "")).strip()
                elif "text" in text:
                    normalized = str(text.get("text", "")).strip()
                elif "content" in text:
                    normalized = str(text.get("content", "")).strip()
                else:
                    normalized = str(text).strip()

            elif isinstance(text, (list, tuple)):
                normalized = " ".join(str(x) for x in text).strip()

            else:
                normalized = str(text).strip()

            # Replace a few common smart punctuation characters that sometimes
            # cause downstream encoding or parser issues in older code paths.
            normalized = (
                normalized.replace("\u2018", "'")
                .replace("\u2019", "'")
                .replace("\u201c", '"')
                .replace("\u201d", '"')
                .replace("\u2013", "-")
                .replace("\u2014", "-")
                .replace("\u00a0", " ")
            )

            return normalized

        except Exception:
            try:
                return str(text)
            except Exception:
                return ""

    # ──────────────────────────────────────────────────────────────
    async def classify_intent(self, text: Any) -> str:
        """
        Asynchronously classify text -> intent tag.
        Example outputs: 'reflect', 'plan', 'predict', 'dream', 'emotion', etc.
        """
        normalized_text = self._normalize_text(text)

        try:
            if self.client and normalized_text:
                prompt = (
                    "You are AION's cognitive classifier.\n"
                    "Given the following text, return one concise lowercase intent keyword "
                    "that best describes what cognitive engine should process it.\n\n"
                    "Valid tags:\n"
                    "- reflect / awareness / conscious\n"
                    "- plan / decision / prediction\n"
                    "- emotion / ethics / energy\n"
                    "- goal / memory / learning / recursion\n"
                    "- code / amend / dna / knowledge / record / qqc\n"
                    "- identity / dream / avatar / situational\n"
                    "- privacy / safety / ledger / verify\n\n"
                    f'Text: "{normalized_text}"\n\n'
                    "Respond with ONE keyword only."
                )

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are AION's semantic intent classifier."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=8,
                )

                content = response.choices[0].message.content if response and response.choices else None
                tag = str(content or "").strip().lower()

                if not tag:
                    tag = self._symbolic_fallback(normalized_text)

                logger.debug(f"[LLMClassifier] -> {tag}")

            elif self.quantum_atom and normalized_text:
                try:
                    tag = await self.quantum_atom.resonate_intent(normalized_text)
                except TypeError:
                    tag = await self.quantum_atom.resonate_intent(text)
                tag = self._normalize_text(tag).lower() or self._symbolic_fallback(normalized_text)
                logger.debug(f"[QuantumAtomClassifier] -> {tag}")

            else:
                tag = self._symbolic_fallback(normalized_text)
                logger.debug(f"[LLMClassifier-Fallback] -> {tag}")

            entry = {
                "input": normalized_text,
                "tag": tag,
                "model": self.model,
            }
            self.history.append(entry)

            try:
                self.ledger.record(
                    {
                        "timestamp": asyncio.get_running_loop().time(),
                        "module": "LLMClassifier",
                        "entry": entry,
                    }
                )
            except Exception:
                pass

            return tag

        except Exception as e:
            logger.error(f"[LLMClassifier] Classification failed: {e}")
            return self._symbolic_fallback(normalized_text)

    # ──────────────────────────────────────────────────────────────
    def _symbolic_fallback(self, text: Any) -> str:
        """
        Simple local heuristic for offline operation.
        Maps keywords -> best-guess intent tags.
        """
        t = self._normalize_text(text).lower()

        if not t:
            return "reflect"

        if any(k in t for k in ["qqc", "stabilize", "field", "resonance"]):
            return "qqc"
        if any(k in t for k in ["plan", "strategy", "goal"]):
            return "plan"
        if any(k in t for k in ["predict", "forecast", "expect"]):
            return "predict"
        if any(k in t for k in ["reflect", "think", "aware", "observe", "symatics"]):
            return "reflect"
        if any(k in t for k in ["dream", "imagine", "sleep"]):
            return "dream"
        if any(k in t for k in ["energy", "vibe", "power"]):
            return "energy"
        if any(k in t for k in ["mood", "feeling", "love", "sad"]):
            return "emotion"
        if any(k in t for k in ["identity", "self", "name", "avatar"]):
            return "identity"
        if any(k in t for k in ["secure", "privacy", "safety"]):
            return "privacy"
        if any(k in t for k in ["ethic", "moral", "right", "wrong"]):
            return "ethics"
        if any(k in t for k in ["memory", "remember", "recall"]):
            return "memory"
        if any(k in t for k in ["learn", "training", "adapt"]):
            return "learning"
        if any(k in t for k in ["code", "patch", "fix", "amend", "refactor"]):
            return "code"
        if any(k in t for k in ["verify", "proof", "prove", "ledger"]):
            return "verify"

        return "reflect"

    # ──────────────────────────────────────────────────────────────
    def last_tag(self) -> Optional[str]:
        """Return the last computed tag, if available."""
        return self.history[-1]["tag"] if self.history else None