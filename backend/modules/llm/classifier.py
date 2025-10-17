# ──────────────────────────────────────────────────────────────
#  Tessaris • AION LLM Classifier (v1.1 Quantum-Ready)
#  Semantic brainstem for AION — interprets intents via OpenAI or Quantum Atom.
#  Can self-adapt to offline symbolic fallback when OpenAI is unavailable.
# ──────────────────────────────────────────────────────────────

import os
import asyncio
import logging
from dotenv import load_dotenv
from openai import AsyncOpenAI

from backend.modules.morphic.ledger import MorphicLedger

load_dotenv()

logger = logging.getLogger("LLMClassifier")


class LLMClassifier:
    """
    AION’s semantic brainstem.
    Performs low-entropy classification of natural-language or symbolic input
    into intent tags used by the CognitiveDispatcher.
    """

    def __init__(self, model: str = None, quantum_atom=None):
        self.model = model or os.getenv("AION_LLM_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("AION_LLM_TEMP", "0.2"))
        self.quantum_atom = quantum_atom  # optional fallback
        self.history = []
        self.ledger = MorphicLedger()

        api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None

        if self.client:
            logger.info(f"✅ LLMClassifier initialized using model: {self.model}")
        else:
            logger.warning("⚠️ OpenAI client not configured — using symbolic fallback only.")

    # ──────────────────────────────────────────────────────────────
    async def classify_intent(self, text: str) -> str:
        """
        Asynchronously classify text → intent tag.
        Example outputs: 'reflect', 'plan', 'predict', 'dream', 'emotion', etc.
        """
        try:
            if self.client:
                # Compose the classification prompt
                prompt = (
                    "You are AION’s cognitive classifier.\n"
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
                    f'Text: "{text}"\n\nRespond with ONE keyword only.'
                )

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are AION’s semantic intent classifier."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=8,
                )

                tag = response.choices[0].message.content.strip().lower()
                logger.debug(f"[LLMClassifier] → {tag}")

            elif self.quantum_atom:
                # Quantum Atom fallback: use internal resonance classifier
                tag = await self.quantum_atom.resonate_intent(text)
                logger.debug(f"[QuantumAtomClassifier] → {tag}")

            else:
                # Offline symbolic heuristic
                tag = self._symbolic_fallback(text)
                logger.debug(f"[LLMClassifier-Fallback] → {tag}")

            # Record classification history and ledger trace
            entry = {"input": text, "tag": tag, "model": self.model}
            self.history.append(entry)

            try:
                self.ledger.record({
                    "timestamp": asyncio.get_event_loop().time(),
                    "module": "LLMClassifier",
                    "entry": entry,
                })
            except Exception:
                pass

            return tag

        except Exception as e:
            logger.error(f"[LLMClassifier] Classification failed: {e}")
            return self._symbolic_fallback(text)

    # ──────────────────────────────────────────────────────────────
    def _symbolic_fallback(self, text: str) -> str:
        """
        Simple local heuristic for offline operation.
        Maps keywords → best-guess intent tags.
        """
        t = text.lower()
        if any(k in t for k in ["plan", "strategy", "goal"]):
            return "plan"
        if any(k in t for k in ["predict", "forecast", "expect"]):
            return "predict"
        if any(k in t for k in ["reflect", "think", "aware", "observe"]):
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
        return "reflect"  # safe neutral fallback

    # ──────────────────────────────────────────────────────────────
    def last_tag(self) -> str:
        """Return the last computed tag, if available."""
        return self.history[-1]["tag"] if self.history else None