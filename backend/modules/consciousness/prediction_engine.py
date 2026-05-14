"""
📄 prediction_engine.py

🔮 Prediction Engine for AION and Symbolic Agents  
Generates symbolic futures, goal-driven forecasts, and timeline branches.
"""

import uuid
import random
import math
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union

import logging
logger = logging.getLogger(__name__)

from backend.modules.dna_chain.switchboard import DNA_SWITCH
def get_glyph_trace():
    from backend.modules.glyphos.glyph_trace_logger import glyph_trace
    return glyph_trace
from backend.modules.soul.soul_laws import get_soul_laws
from backend.modules.consciousness.symbolic_gradient_engine import SymbolicGradientEngine
from backend.modules.knowledge_graph.glyph_feedback_tracer import GlyphFeedbackTracer
from backend.modules.knowledge_graph.brain_map_streamer import BrainMapStreamer
from backend.modules.glyphos.symbolic_entangler import get_entangled_for
from backend.modules.glyphos.glyph_quantum_core import GlyphQuantumCore
from backend.modules.consciousness.gradient_entanglement_adapter import GradientEntanglementAdapter
from backend.modules.knowledge_graph.entanglement_fusion import EntanglementFusion
from backend.modules.codex.codex_trace import CodexTrace
from backend.modules.codex.codex_metrics import calculate_glyph_cost as estimate_glyph_cost
from backend.modules.codex.codex_metrics import CodexMetrics
from backend.modules.codex.metric_utils import estimate_glyph_cost
from backend.modules.lean.lean_proofverifier import is_logically_valid
from backend.modules.codex.rewrite_executor import apply_rewrite
from backend.modules.codex.dna_mutation_tracker import add_dna_mutation
from backend.modules.symbolic.symbolic_broadcast import broadcast_glyph_event
from backend.modules.codex.codexlang_rewriter import CodexLangRewriter, suggest_rewrite_candidates
from backend.modules.prediction.suggestion_engine import suggest_simplifications
from backend.modules.symbolic.symbolic_meaning_tree import SymbolicMeaningTree
from backend.modules.symbolnet.symbolnet_utils import concept_match, semantic_distance
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
def get_emit_qwave_beam_ff():
    from backend.modules.glyphwave.emit_beam import emit_qwave_beam as emit_qwave_beam_ff
    return emit_qwave_beam_ff
from backend.modules.spe.spe_bridge import recombine_from_beams, repair_from_drift, maybe_autofuse

def get_prediction_kg_writer():
    try:
        return get_kg_writer()
    except Exception as e:
        logging.warning(f"[PredictionEngine] Failed to get KnowledgeGraphWriter instance: {e}")
        return None

try:
    from backend.modules.tessaris.tessaris_engine import TessarisEngine
    from backend.modules.dream_core import DreamCore
except ImportError:
    MemoryEngine, TessarisEngine, DreamCore = None, None, None

DNA_SWITCH.register(__file__)

# ✅ Lazy import wrapper
def get_estimate_codex_cost():
    from backend.modules.codex.codex_executor import estimate_codex_cost
    return estimate_codex_cost

class PredictionEngine:
    def __init__(self, container_id: str = "global", memory_engine=None, tessaris_engine=None, dream_core=None):
        log.info("[PredictionEngine] Initialized - ready for feasibility assessments.")
        self.container_id = container_id
        self.memory_engine = memory_engine or (MemoryEngine() if MemoryEngine else None)
        self.tessaris_engine = tessaris_engine or (TessarisEngine() if TessarisEngine else None)
        self.dream_core = dream_core or (DreamCore() if DreamCore else None)
        self.soul_laws = get_soul_laws()
        self.logger = logging.getLogger(__name__)

        self.gradient_engine = SymbolicGradientEngine()
        self.feedback_tracer = GlyphFeedbackTracer(container_id=self.container_id)
        self.entanglement_adapter = GradientEntanglementAdapter()
        self.entanglement_fusion = EntanglementFusion()
        self.brain_streamer = BrainMapStreamer()
        self.quantum_core = GlyphQuantumCore(container_id=self.container_id)
        self.history = []

    @property
    def logger(self):
        # fallback if __init__ was skipped
        return getattr(self, "_logger", logging.getLogger(__name__))

    @logger.setter
    def logger(self, value):
        self._logger = value

    def detects_conflicting_predicts(current_text, glyphs):
        for glyph in glyphs:
            if glyph["text"] != current_text and glyph["text"] in current_text:
                return True
        return False

    def extract_prediction_path(text):
        # crude fallback - customize for your AST/glyph format
        try:
            return text.split("Predicts(")[1].split(")")[0]
        except:
            return "Unknown"

    def score_predictive_path(path):
        # stub - replace with actual SQI scoring logic if needed
        return {
            "stability": round(random.uniform(0.4, 1.0), 3),
            "resonance": round(random.uniform(0.2, 0.9), 3),
            "entropy": round(random.uniform(0.1, 0.7), 3),
        }


    def assess_feasibility(self, goal: Union[str, dict]) -> float:
        """
        Returns a pseudo-probabilistic feasibility score (0-1)
        based on symbolic goal complexity and random harmonics.
        """
        if not goal:
            return 0.0

        goal_text = goal if isinstance(goal, str) else str(goal)
        complexity = min(len(goal_text) / 64.0, 1.0)  # heuristic: long goals = harder
        base_resonance = 1.0 - (complexity * 0.5)
        noise = random.uniform(-0.1, 0.1)

        feasibility = max(0.0, min(1.0, base_resonance + noise))
        log.info(f"[PredictionEngine] Feasibility({goal_text}) = {feasibility:.3f}")
        return feasibility

    def _run_prediction_on_ast(self, ast_or_raw: dict) -> dict:
        from backend.modules.codex.codex_metrics import CodexMetrics
        from backend.modules.lean.lean_tactic_suggester import suggest_tactics
        from backend.modules.codex.codex_lang_rewriter import suggest_rewrite_candidates
        from backend.modules.codex.codex_trace import CodexTrace
        inject_trace_metadata = None
        try:
            from backend.modules.knowledge_graph.kg_writer_singleton import inject_trace_metadata
        except ImportError:
            pass

        if ast_or_raw is None:
            return {"status": "error", "detail": "No AST provided"}

        try:
            # ✅ If it's already normalized
            if ast_or_raw.get("type") in {"logic_block", "glyph_program"}:
                result = self._analyze_ast_tree(ast_or_raw)

            # ⚛ Electron prediction logic
            elif "electrons" in ast_or_raw:
                result = self._analyze_electron_predictions(ast_or_raw["electrons"])

            else:
                # 🧠 Normalize lowercase CodexLang AST if needed
                normalized = self._normalize_codexlang_ast(ast_or_raw)
                result = self._analyze_ast_tree(normalized)

            # --- 🔍 CONTRADICTION INJECTION ---
            self._inject_contradiction_flags(ast_or_raw)

            # --- 🧠 SQI SCORING ---
            self._compute_sqi_scores(ast_or_raw)

            # --- 🎞️ TRACE REPLAY INJECTION ---
            self._inject_trace_metadata(ast_or_raw, result)

            # --- 🔁 AUTO-REWRITE ON CONTRADICTION ---
            if result.get("status") == "contradiction":
                goal_repr = ast_or_raw.get("repr") or ast_or_raw.get("raw") or str(ast_or_raw)
                tactics = suggest_tactics(goal_repr, context=[])

                rewrites = suggest_rewrite_candidates(ast_or_raw)
                if rewrites:
                    best = rewrites[0]
                    rewritten_ast = best.get("ast")
                    label = best.get("label")

                    # Log rewrite trace
                    CodexTrace.log_prediction("⊥", "rewrite", label)

                    # Inject trace
                    inject_trace_metadata(result.get("containerId"), {
                        "type": "rewrite",
                        "from": goal_repr,
                        "to": label,
                        "tactics": tactics
                    })

                    # ♻️ Retry prediction with rewritten AST
                    rewritten_result = self._run_prediction_on_ast(rewritten_ast)
                    rewritten_result["original"] = goal_repr
                    rewritten_result["wasRewritten"] = True
                    return rewritten_result

            return result

        except Exception as e:
            return {
                "status": "error",
                "detail": f"Unknown AST structure: {e}"
            }

    def _normalize_codexlang_ast(self, ast: dict) -> dict:
        """
        Converts lowercase internal CodexLang-style AST to normalized form.
        Example: 'forall' -> 'ForAll', 'predicate' -> Codex predicate structure.
        """
        if ast["type"] == "forall":
            return {
                "type": "ForAll",
                "var": ast["variable"],
                "body": self._normalize_codexlang_ast(ast["body"])
            }
        elif ast["type"] == "implies":
            return {
                "type": "Implies",
                "left": self._normalize_codexlang_ast(ast["left"]),
                "right": self._normalize_codexlang_ast(ast["right"])
            }
        elif ast["type"] == "predicate":
            return {
                "type": "call",
                "name": ast["name"],
                "args": [{"type": "variable", "value": arg} for arg in ast["args"]]
            }
        elif ast["type"] == "not":
            return {
                "type": "not",
                "value": self._normalize_codexlang_ast(ast["value"])
            }
        elif ast["type"] == "and":
            return {
                "type": "and",
                "left": self._normalize_codexlang_ast(ast["left"]),
                "right": self._normalize_codexlang_ast(ast["right"])
            }
        elif ast["type"] == "or":
            return {
                "type": "or",
                "left": self._normalize_codexlang_ast(ast["left"]),
                "right": self._normalize_codexlang_ast(ast["right"])
            }
        else:
            raise ValueError(f"Unsupported node type: {ast.get('type')}")

    def _analyze_ast_tree(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run AST-level prediction logic.
        Includes contradiction detection, simplification suggestions,
        and basic inference reasoning for logic-based glyphs.
        """

        def detect_contradictions(node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            def ast_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
                if a.get("type") != b.get("type"):
                    return False
                if a.get("type") in {"symbol", "variable"}:
                    return a.get("value") == b.get("value")
                if a.get("type") == "call":
                    return (
                        a.get("name") == b.get("name") and
                        all(ast_equal(x, y) for x, y in zip(a.get("args", []), b.get("args", [])))
                    )
                if a.get("type") == "not":
                    return ast_equal(a.get("value"), b.get("value"))
                if a.get("type") in {"and", "or", "implies", "iff"}:
                    return ast_equal(a.get("left"), b.get("left")) and ast_equal(a.get("right"), b.get("right"))
                return False

            # Detect: P(x) ∧ ¬P(x)
            if node.get("type") == "and":
                left = node.get("left")
                right = node.get("right")
                if right and right.get("type") == "not":
                    if ast_equal(left, right.get("value")):
                        return {
                            "expression": node,
                            "reason": "⚛ Contradiction: P(x) ∧ ¬P(x) detected",
                            "score": 0.95
                        }
            return None

        # ✅ New logic: handle ForAll (universal quantifier)
        if ast.get("type") == "ForAll":
            var_name = ast.get("var")
            body = ast.get("body")

            if not var_name or not body:
                return {
                    "status": "error",
                    "detail": "Malformed ForAll: missing 'var' or 'body'"
                }

            example = { "type": "variable", "value": var_name }

            def substitute(node):
                if node.get("type") == "variable" and node.get("value") == var_name:
                    return example
                elif node.get("type") == "call":
                    return {
                        "type": "call",
                        "name": node["name"],
                        "args": [substitute(arg) for arg in node.get("args", [])]
                    }
                elif node.get("type") in {"not", "symbol"}:
                    return { **node, "value": substitute(node["value"]) } if "value" in node else node
                elif node.get("type") in {"and", "or", "implies", "iff"}:
                    return {
                        "type": node["type"],
                        "left": substitute(node["left"]),
                        "right": substitute(node["right"])
                    }
                elif node.get("type") == "predicate":
                    return {
                        "type": "predicate",
                        "operator": node["operator"],
                        "operands": [substitute(arg) for arg in node.get("operands", [])]
                    }
                return node

            substituted = substitute(body)
            return _analyze_ast_tree(substituted)

        # ✅ Otherwise, continue normally
        contradiction = detect_contradictions(ast)
        if contradiction:
            return {
                "status": "contradiction",
                "detail": contradiction["reason"],
                "score": contradiction["score"]
            }

        return {
            "status": "ok",
            "detail": "No contradictions detected"
        }


    def _analyze_electron_predictions(electrons: List[dict]) -> dict:
        best_electron = None
        best_confidence = -1.0
        prediction_summary = []

        for electron in electrons:
            glyphs = electron.get("glyphs", [])
            label = electron.get("meta", {}).get("label", "unknown")

            for glyph in glyphs:
                if glyph["type"] == "predictive":
                    prediction_summary.append({
                        "label": label,
                        "value": glyph["value"],
                        "confidence": glyph["confidence"]
                    })

                    if glyph["confidence"] > best_confidence:
                        best_confidence = glyph["confidence"]
                        best_electron = {
                            "label": label,
                            "value": glyph["value"],
                            "confidence": glyph["confidence"]
                        }

        if best_electron:
            return {
                "status": "prediction",
                "best_path": best_electron,
                "summary": prediction_summary
            }
        else:
            return {
                "status": "error",
                "detail": "No predictive glyphs found in electrons"
            }

    def _inject_contradiction_flags(self, ast_or_raw: dict):
        """Flag glyphs that contradict others (simple implication or mutually exclusive logic)."""
        glyphs = ast_or_raw.get("glyph_grid", [])
        contradiction_pairs = []

        # Example: simple same-subject, different prediction detection
        prediction_map = {}

        for glyph in glyphs:
            text = glyph.get("text", "")
            if "Predicts" in text and "Electron" in text:
                for line in text.split("∨"):
                    parts = line.split("Predicts")
                    if len(parts) > 1:
                        prediction = parts[-1].strip().strip("()\"")
                        if prediction in prediction_map:
                            contradiction_pairs.append((prediction, prediction_map[prediction]))
                        else:
                            prediction_map[prediction] = glyph["id"]

        # Inject into glyph metadata
        for glyph in glyphs:
            glyph["metadata"] = glyph.get("metadata", {})
            for p1, p2 in contradiction_pairs:
                if p1 in glyph["text"] or p2 in glyph["text"]:
                    glyph["metadata"]["contradiction"] = True

    def _compute_sqi_scores(self, ast_or_raw: dict):
        """Inject symbolic quality scores into prediction glyphs."""
        import random  # Replace with real scoring later

        glyphs = ast_or_raw.get("glyph_grid", [])
        for glyph in glyphs:
            if "Predicts" in glyph.get("text", ""):
                glyph["metadata"] = glyph.get("metadata", {})
                glyph["metadata"]["sqi_score"] = {
                    "stability": round(random.uniform(0.7, 1.0), 3),
                    "entropy": round(random.uniform(0.0, 0.4), 3),
                    "resonance": round(random.uniform(0.5, 1.0), 3),
                }

    def _inject_trace_metadata(self, ast_or_raw: dict, result: dict):
        """Inject result summary into trace metadata for CodexHUD / GHX replay."""
        trace = ast_or_raw.setdefault("traceMetadata", {})
        trace["predictionInjected"] = True
        trace["predictionResult"] = result

    def _trigger_rewrite_if_needed(self, ast_or_raw: dict, result: dict) -> None:
        """
        Check the AST or raw input for logical contradictions or simplification opportunities.
        If any are found, annotate the result with rewrite suggestions.
        """
        from backend.modules.prediction.suggestion_engine import suggest_simplifications

        suggestions = suggest_simplifications(ast_or_raw)

        if suggestions:
            result["rewriteSuggestions"] = suggestions
            result["status"] = "rewrite_suggested"

    def detect_contradictions(node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Detects contradictions in logic ASTs, such as: P(x) ∧ ¬P(x)
        Returns a contradiction report if found, else None.
        """

        def ast_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
            # Recursive structural equality for AST nodes
            if a.get("type") != b.get("type"):
                return False
            if a.get("type") in {"symbol", "variable"}:
                return a.get("value") == b.get("value")
            if a.get("type") == "call":
                return (
                    a.get("name") == b.get("name") and
                    all(ast_equal(x, y) for x, y in zip(a.get("args", []), b.get("args", [])))
                )
            if a.get("type") == "not":
                return ast_equal(a.get("value"), b.get("value"))
            if a.get("type") in {"and", "or", "implies", "iff"}:
                return ast_equal(a.get("left"), b.get("left")) and ast_equal(a.get("right"), b.get("right"))
            return False

        # Check for pattern: P(x) ∧ ¬P(x)
        if node.get("type") == "and":
            left = node.get("left")
            right = node.get("right")
            if right and right.get("type") == "not":
                if ast_equal(left, right.get("value")):
                    return {
                        "expression": node,
                        "reason": "⚛ Contradiction: P(x) ∧ ¬P(x) detected",
                        "score": 0.95
                    }
        return None

from backend.modules.symbolic.hst.hst_injection_utils import inject_hst_to_container

from backend.modules.codex.codex_metrics import record_sqi_score_event  # ✅ add this at the top with other imports

class PredictionEngine:
    logger = logging.getLogger(__name__) 
    ...

    def _compute_sqi_fields(self, prediction: dict) -> dict:
        """
        Compute symbolic SQI drift and quality score (qscore).
        Currently stubbed: drift = inverse confidence, qscore = scaled confidence.
        """
        confidence = prediction.get("confidence", 0.5)
        drift = round(1.0 - confidence, 3)         # drift = inverse confidence
        qscore = round(confidence * 0.9 + 0.1, 3)  # bias high confidence into qscore
        return {"drift": drift, "qscore": qscore}

    def run_prediction_on_container(self, container: Dict[str, Any], context: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Full prediction pipeline with:
        - AST inspection
        - Contradiction detection (glyph + logic)
        - Rewrite suggestion
        - .dc.json trace injection
        - SQI scoring
        - Lean proof verification
        - Optional live application + DNA mutation
        - Electron glyph prediction (atom containers)
        - HST (SymbolicMeaningTree) injection
        """
        contradiction_found = False
        scored = []
        electron_predictions = []

        # 🧠 Check for glyph-level contradictions, SQI scoring, and semantic similarity
        goal_label = container.get("goal", {}).get("label") or "energy"  # Replace "energy" if needed

        for glyph in container.get("glyph_grid", []):
            text = glyph.get("text", "")
            label = glyph.get("label") or text
            metadata = glyph.setdefault("metadata", {})

            # SQI score from path prediction
            if "Predicts" in text:
                path = extract_prediction_path(text)
                score = score_predictive_path(path)
                metadata["sqiScore"] = score

                # Contradiction detection
                if "¬" in text or detects_conflicting_predicts(text, container["glyph_grid"]):
                    metadata["contradictionDetected"] = True
                    contradiction_found = True

            # 🌐 Inject SymbolNet scores
            try:
                from backend.modules.symbolnet.symbolnet_utils import concept_match, semantic_distance
                metadata["semantic_score"] = concept_match(label, goal_label)
                metadata["semantic_distance"] = semantic_distance(label, goal_label)
            except Exception as e:
                print(f"[PredictionEngine] ⚠️ Semantic scoring failed for glyph '{label}': {e}")

            try:
                # 🔄 Lazy getter to avoid circular import
                from backend.modules.codex.codex_executor import _get_tessaris  
                tessaris = _get_tessaris()
                if tessaris:
                    glyphs = [g.get("text", "") for g in container.get("glyph_grid", []) if g.get("text")]
                    if glyphs:
                        intents = tessaris.extract_intents_from_glyphs(
                            glyphs,
                            metadata={"origin": "photon", "container_id": container.get("id")}
                        )
                        container.setdefault("traceMetadata", {})["tessarisIntents"] = intents
                        logger.info(f"[PredictionEngine] Tessaris intents extracted: {intents}")
            except Exception as e:
                logger.warning(f"[PredictionEngine] Tessaris alignment failed: {e}")

        # ⚛️ Electron-based predictive glyph selection with SymbolNet scoring
        for e in container.get("electrons", []):
            label = e.get("meta", {}).get("label", "unknown")
            best = max(e.get("glyphs", []), key=lambda g: g.get("confidence", 0), default=None)
            if best:
                prediction = {
                    "electron": label,
                    "selected_prediction": best["value"],
                    "confidence": best["confidence"]
                }

                # 🎯 Add SymbolNet semantic scores relative to container goal
                try:
                    goal_label = container.get("goal", {}).get("label") or "energy"
                    scores = self.enrich_with_symbolnet_scores(best["value"], goal_label)
                    prediction.update(scores)
                except Exception as e:
                    print(f"[PredictionEngine] ⚠️ Failed to enrich electron prediction with SymbolNet scores: {e}")

                electron_predictions.append(prediction)

        if electron_predictions:
            container.setdefault("trace", {}).setdefault("predictions", {})["electrons"] = electron_predictions

        # 🧠 Print Top 3 electrons by SQI score if available
        try:
            top3 = sorted(electron_predictions, key=lambda x: x.get("confidence", 0), reverse=True)[:3]
            print("[PredictionEngine] Top 3 electrons by SQI confidence:")
            for ep in top3:
                print(f" * {ep['electron']} -> {ep['selected_prediction']} ({ep['confidence']:.3f})")
        except Exception as e:
            print(f"[PredictionEngine] ⚠️ Failed to print top electrons: {e}")

        # 🌐 Beam emission + SQI logging
        try:
            from backend.modules.consciousness.prediction_engine import emit_qwave_beam_ff
            from backend.modules.codex.codex_metrics import record_sqi_score_event

            container_id = container.get("id", "unknown")
            first_electron = container.get("electrons", [{}])[0]
            glyphs = first_electron.get("glyphs", [])
            best_glyph = max(glyphs, key=lambda g: g.get("confidence", 0), default={})

            glyph_id = best_glyph.get("id", best_glyph.get("value", "unknown"))
            qscore = best_glyph.get("confidence", 0.0)
            drift = 1.0 - qscore  # simple drift placeholder

            payload = {
                "container_id": container_id,
                "glyph_id": glyph_id,
                "drift": drift,
                "qscore": qscore,
                "source": context or "prediction_engine",
            }

            # 🚀 Emit beam + log metrics
            emit_qwave_beam_ff("prediction_engine", payload, context=context)
            record_sqi_score_event(
                container_id, glyph_id, drift, qscore, context or "prediction_engine"
            )

        except Exception as beam_err:
            self.logger.warning(f"[PredictionEngine] ⚠️ Beam emission block failed: {beam_err}")

        # 📘 Logic-level contradiction detection + rewrite scoring
        expr = container.get("logic", {}).get("expression")
        if expr:
            suggestions = suggest_rewrite_candidates(expr)

            for s in suggestions:
                original = s.get("from")
                proposed = s.get("to")
                reason = s.get("reason", "unspecified")

                score = self.score_rewrite_suggestion(original, proposed, container)
                valid = is_logically_valid(proposed)

                trace_entry = {
                    "from": original,
                    "to": proposed,
                    "reason": reason,
                    "entropy_delta": score["entropy_delta"],
                    "goal_match_score": score["goal_match_score"],
                    "rewrite_success_prob": score["rewrite_success_prob"],
                    "logically_valid": valid
                }
                scored.append(trace_entry)

                # Inject into .dc.json trace
                container.setdefault("trace", {}).setdefault("predictions", {}).setdefault("rewrites", []).append(trace_entry)

                # ✅ Apply live rewrite if valid and confident
                if valid and score["rewrite_success_prob"] > 0.8:
                    apply_rewrite(container.get("id"), proposed)
                    add_dna_mutation(original, proposed, reason=reason)
                    inject_sqi_scores_into_container(container)  

                # 🌐 Broadcast via Codex WebSocket
                broadcast_glyph_event(
                    event_type="prediction",
                    glyph=trace_entry.get("glyph") or trace_entry.get("proposed"),
                    container_id=container.get("id"),
                    coord=trace_entry.get("coord", "0:0"),
                    extra={
                        "score": score,
                        "reason": reason,
                        "origin": context or "prediction_engine"
                    }
                )

        # 🎞️ Inject trace metadata
        container.setdefault("traceMetadata", {})["predictionResult"] = {
            "status": "contradiction" if contradiction_found else "ok",
            "sqiTrace": True,
            "timestamp": time.time(),
            "context": context or "prediction_engine"
        }

        # ⬁ Suggest simplifications if glyph-level contradiction was found
        if contradiction_found:
            container["traceMetadata"]["rewriteSuggestions"] = PredictionEngine.suggest_simplifications(container)

        # ✅ Inject SymbolicMeaningTree after prediction phase
        inject_hst_to_container(container, context={
            "container_path": container.get("id", "unknown"),
            "coord": container.get("coord", "0:0"),
            "source": context or "prediction_engine"
        })

        try:
            from backend.modules.symbolic.symbol_tree_generator import build_symbolic_tree_from_container
            tree = build_symbolic_tree_from_container(container)
            predicted_paths = self.generate_probable_paths(tree)

            # 🎯 Enrich each predicted path with SymbolNet scores relative to goal
            goal_label = container.get("goal", {}).get("label", "energy")
            for path in predicted_paths:
                label = path.get("label")
                if label:
                    try:
                        scores = self.enrich_with_symbolnet_scores(label, goal_label)
                        path.update(scores)
                    except Exception as score_err:
                        print(f"[PredictionEngine] ⚠️ Failed to score path '{label}': {score_err}")

            container["predicted_paths"] = predicted_paths
            self.logger.info(f"[PredictionEngine] Injected {len(predicted_paths)} probable paths")

            # 🌐 Stream HST via WebSocket to GHX/QFC
            from backend.modules.symbolic.hst.hst_websocket_streamer import stream_hst_to_websocket
            stream_hst_to_websocket(
                container_id=container.get("id", "unknown"),
                tree=tree,
                context="prediction_engine"
            )

        except Exception as path_err:
            self.logger.warning(f"[PredictionEngine] ⚠️ Failed to generate probable paths: {path_err}")
            tree = None  # ensure tree is defined, even if failed

        # 🛰️ Broadcast and enrich replay trails if available
        try:
            from backend.modules.symbolic.hst.hst_websocket_streamer import broadcast_replay_paths
            replay_paths = container.get("trace", {}).get("replayPaths", [])
            goal_label = container.get("goal", {}).get("label", "energy")

            # 🎯 Add SymbolNet scores to each replay path
            for path in replay_paths:
                label = path.get("label")
                scores = self.enrich_with_symbolnet_scores(label, goal_label)
                path.update(scores)

                # 🔁 🔥 Optional SQI Flags
                if scores.get("concept_match_score", 0) > 0.9:
                    path["sqi_lock"] = True
                if scores.get("semantic_distance", 1.0) < 0.2:
                    path["entropy_spike"] = True

            # 📦 Inject SymbolNet overlay for GHX/QFC visualization
            enriched_overlay = []
            for path in replay_paths:
                label = path.get("label")
                scores = self.enrich_with_symbolnet_scores(label, goal_label)
                overlay_entry = {
                    "label": label,
                    **scores,
                    "highlight": scores.get("concept_match_score", 0) > 0.7,
                    "intensity": scores.get("concept_match_score", 0)
                }
                enriched_overlay.append(overlay_entry)

            container.setdefault("traceMetadata", {})["symbolnetOverlay"] = {
                "replayPaths": enriched_overlay,
                "source": "PredictionEngine"
            }

            if replay_paths:
                broadcast_replay_paths(
                    container_id=container.get("id", "unknown"),
                    replay_paths=replay_paths,
                    context="prediction_engine"
                )

        except Exception as e:
            print(f"[PredictionEngine] ⚠️ Failed to broadcast replay trails: {e}")

        # 🧠 Inject SQI scores into container-level structure (including electrons)
        try:
            from backend.modules.sqi.sqi_scorer import inject_sqi_scores_into_container
            inject_sqi_scores_into_container(container)
        except Exception as sqi_err:
            print(f"[PredictionEngine] ⚠️ Failed to inject SQI scores: {sqi_err}")

        # 🧠 Inject SQI scores into container-level structure (including electrons)
        try:
            from backend.modules.sqi.sqi_scorer import inject_sqi_scores_into_container
            inject_sqi_scores_into_container(container)
        except Exception as sqi_err:
            print(f"[PredictionEngine] ⚠️ Failed to inject SQI scores: {sqi_err}")

        # ✅ Emit QWave Beam for prediction output (normalized via WaveState wrapper + SQI scoring)
        try:
            top_prediction = electron_predictions[0] if electron_predictions else None
            if top_prediction:
                # 🔹 Compute SQI fields
                sqi_fields = self._compute_sqi_fields(top_prediction)

                # 🔹 Log into metrics
                record_sqi_score_event(container_id, glyph_id, drift, qscore, source)

                # 🔹 Emit beam with SQI metadata (lazy import to avoid circular dependency)
                try:
                    from backend.modules.glyphwave.emit_beam import emit_qwave_beam as emit_qwave_beam_ff
                    emit_fn = get_emit_qwave_beam_ff()
                    emit_fn(
                        source="prediction_engine",
                        payload={
                            "wave_id": f"pred_{top_prediction['electron']}_{int(time.time()*1000)}",
                            "event": "prediction",
                            "mutation_type": "forecast",
                            "container_id": container.get("id"),
                            "confidence": top_prediction.get("confidence"),
                            "electron": top_prediction.get("electron"),
                            "selected_prediction": top_prediction["selected_prediction"],
                            "drift": sqi_fields["drift"],
                            "qscore": sqi_fields["qscore"],
                        },
                        context={"container_id": container.get("id")}
                    )
                except Exception as emit_err:
                    print(f"[PredictionEngine] ⚠️ Failed to emit QWave beam: {emit_err}")
        except Exception as beam_err:
            print(f"[PredictionEngine] ⚠️ Beam emission block failed: {beam_err}")

        return {
            "status": "contradiction" if contradiction_found else "ok",
            "rewrites": scored,
            "electron_predictions": electron_predictions,
            "detail": "Contradiction(s) flagged in glyphs" if contradiction_found else "No contradictions detected"
        }

    def enrich_with_symbolnet_scores(self, label: str, goal_label: str) -> Dict[str, float]:
        if not label or not goal_label:
            return {"semantic_score": 0.0, "semantic_distance": 1.0}
        return {
            "semantic_score": concept_match(label, goal_label),
            "semantic_distance": semantic_distance(label, goal_label)
        }

    def generate_probable_paths(self, tree: SymbolicMeaningTree) -> List[Dict[str, Any]]:
        """
        Generate probable reasoning or mutation paths from a symbolic tree.
        Uses goal_match, entropy, entanglement to project likely futures.
        """
        probable_paths = []

        # Select top 3 high goal_match nodes
        top_nodes = sorted(
            tree.node_index.values(),
            key=lambda n: n.morphic_overlay.get("goal_match", 0),
            reverse=True,
        )[:3]

        for i, node in enumerate(top_nodes):
            path = {
                "path_id": f"future_{i+1:03}",
                "glyph_sequence": [node.glyph_id],
                "goal_trace": [node.morphic_overlay.get("node_type", "unknown")],
                "mutation_trail": node.morphic_overlay.get("mutation_path", []),
                "source_node": node.id,
                "predicted_entropy": node.morphic_overlay.get("entropy"),
            }
            probable_paths.append(path)

        return probable_paths    

    @classmethod
    def score_rewrite_suggestion(cls, original: str, proposed: str, container: Dict[str, Any]) -> Dict[str, float]:
        """
        Score rewrite on:
        - Entropy reduction
        - Goal alignment
        - Rewrite success probability
        """
        original_entropy = cls.estimate_entropy(original)
        proposed_entropy = cls.estimate_entropy(proposed)
        goal_match = cls.estimate_goal_alignment(proposed, container)

        return {
            "entropy_delta": original_entropy - proposed_entropy,
            "goal_match_score": goal_match,
            "rewrite_success_prob": min(1.0, goal_match + (original_entropy - proposed_entropy) / 10.0)
        }

    @staticmethod
    def estimate_entropy(expr: str) -> float:
        # Very simple entropy proxy based on length and symbolic density
        length = len(expr)
        symbols = len([c for c in expr if not c.isalnum()])
        return (symbols + 1) * (length ** 0.5)

    @staticmethod
    def estimate_goal_alignment(expr: str, container: Dict[str, Any]) -> float:
        goals = container.get("goals", [])
        matches = [g for g in goals if g in expr]
        return min(1.0, len(matches) / max(1, len(goals)))

    @staticmethod
    def load_container_from_path(path: str) -> dict:
        from backend.modules.utils.file_loader import load_dc_container
        return load_dc_container(path)

    def select_best_prediction(outcomes: list, context: dict) -> dict:
        """
        Evaluate list of outcome dicts and choose the most optimal one.
        Applies SQI-inspired logic score, entropy penalty, cost penalty,
        and goal alignment reward.
        """
        scored = []

        for outcome in outcomes:
            glyph = outcome.get("glyph", {})
            logic = outcome.get("logic_score", 0) or 0
            entropy = outcome.get("entropy_delta", 0) or 0
            goal_alignment = outcome.get("goal_score", 0) or 0
            cost = estimate_glyph_cost(glyph) if glyph else 0

            score = (
                (logic * 2.0) -
                (entropy * 1.5) -
                (cost * 0.8) +
                (goal_alignment * 2.5)
            )

            scored.append((score, outcome))

        if not scored:
            logger.warning("[Prediction] No outcomes could be scored. Choosing randomly.")
            return random.choice(outcomes)

        scored.sort(reverse=True, key=lambda x: x[0])
        best_score, best_outcome = scored[0]

        # Optional debug output
        logger.debug(f"[Prediction] Best score: {best_score} for outcome: {best_outcome.get('label', 'N/A')}")

        return best_outcome

    async def forecast_hyperdrive(self, hyperdrive_engine) -> Dict:
        """
        Forecasts symbolic hyperdrive drift, resonance costs, and timeline stability.
        Integrates SQI coherence, drift costs, Codex predictions, entangled KG biasing,
        and optionally injects corrective stabilization glyphs if drift exceeds threshold.
        """
        try:
            # 🧠 Pull core state info
            coherence = getattr(hyperdrive_engine, "coherence", 0.0)
            drift = 1.0 - coherence
            sqi_engine = getattr(hyperdrive_engine, "sqi_engine", None)
            container_id = getattr(hyperdrive_engine, "container_id", "global")

            # 🔍 Estimate drift cost if SQIReasoningEngine supports it
            drift_cost = 1.0
            if sqi_engine and hasattr(sqi_engine, "estimate_drift_cost"):
                drift_cost = sqi_engine.estimate_drift_cost(drift=drift)

            # ✅ Fallback resonance estimate if missing
            resonance_estimate = None
            if sqi_engine and hasattr(sqi_engine, "get_last_prediction"):
                try:
                    last_pred = sqi_engine.get_last_prediction()
                    resonance_estimate = last_pred.get("resonance_estimate") if last_pred else None
                except Exception:
                    resonance_estimate = None
            if resonance_estimate is None:
                # Seed from engine resonance buffer or wave frequency
                if hasattr(hyperdrive_engine, "resonance_filtered") and hyperdrive_engine.resonance_filtered:
                    resonance_estimate = sum(hyperdrive_engine.resonance_filtered[-3:]) / min(3, len(hyperdrive_engine.resonance_filtered))
                else:
                    resonance_estimate = getattr(hyperdrive_engine, "wave_frequency", 1.0)
                print(f"⚠️ Fallback SQI prediction used: resonance_estimate={resonance_estimate:.4f}")

            # 🎯 Predict symbolic correction paths
            current_glyph = getattr(hyperdrive_engine, "current_glyph", "⧖ hyperdrive:tick")
            predictions = await self.generate_future_paths(
                current_glyph=current_glyph,
                container_path=container_id,
                goal="Stabilize Hyperdrive",
                coord="hyperdrive-core",
                emotion="neutral",
                num_paths=2,
                agent_id="hyperdrive"
            )

            # 🔗 Entangled KG Bias: Adjust based on drift
            bias_score = max(0.0, min(1.0, 1.0 - drift))
            await self.entanglement_fusion.propagate_gradient(
                glyph_id=current_glyph,
                gradient_vector={"hyperdrive_bias": bias_score, "drift_cost": drift_cost, "resonance_estimate": resonance_estimate},
                source_agent="hyperdrive"
            )

            # 🛠 Automatic corrective glyph injection if drift is critical
            if drift > 0.6:
                corrective_glyph = f"{current_glyph} ⧖ SQI↺[stabilize]"
                print(f"⚠️ High drift detected ({drift:.2f}) -> Injecting corrective glyph: {corrective_glyph}")
                try:
                    from backend.modules.codex.codex_executor import trigger_glyph
                    await trigger_glyph(
                        glyph=corrective_glyph,
                        container_id=container_id,
                        metadata={"origin": "forecast_hyperdrive", "action": "auto_stabilize"}
                    )
                except Exception as e:
                    print(f"⚠️ Corrective glyph injection failed: {e}")

            # 📊 Return structured forecast
            return {
                "coherence": coherence,
                "drift": drift,
                "drift_cost": drift_cost,
                "resonance_estimate": resonance_estimate,  # ✅ Added fallback resonance field
                "predictions": predictions,
                "recommendation": "Boost SQI tuning" if drift > 0.5 else "Stable",
                "auto_injected": drift > 0.6,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            print(f"⚠️ Hyperdrive forecast failed: {e}")
            return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

    async def generate_future_paths(
        self,
        current_glyph: str,
        container_path: Optional[str] = None,
        goal: Optional[str] = None,
        coord: Optional[str] = None,
        emotion: Optional[str] = None,
        num_paths: int = 3,
        agent_id: str = "local"
    ) -> List[Dict]:
        """Generates symbolic futures with KG rebiasing, collapse feedback, and live streaming."""
        predictions = []
        goal_vector = self._embed_goal(goal)
        entangled_glyphs = get_entangled_for(current_glyph)
        qbit = self.quantum_core.generate_qbit(current_glyph, coord or "unknown")

        estimate_codex_cost = get_estimate_codex_cost()

        for i in range(num_paths):
            future_glyph = self._predict_with_quantum(current_glyph, goal_vector, entangled_glyphs, qbit)
            confidence = self._estimate_confidence(current_glyph, future_glyph, emotion, goal_vector)

            prediction = {
                "id": str(uuid.uuid4()),
                "tick": datetime.now(timezone.utc).isoformat(),
                "input_glyph": current_glyph,
                "predicted_glyph": future_glyph,
                "confidence": confidence,
                "goal": goal,
                "emotion_context": emotion,
                "container_path": container_path,
                "coord": coord,
                "qbit_id": qbit["qbit_id"],
                "qbit_state": qbit["state"],
                "entangled_ancestry": entangled_glyphs,
                "soul_law_violation": self._check_soul_laws(future_glyph),
                "codex_cost_estimate": estimate_codex_cost(future_glyph),
                "is_dream_pattern": self._matches_dream_trace(future_glyph),
                "multiverse_label": "⚛ superposed" if qbit["state"] == "superposed" else ("↔ entangled" if entangled_glyphs else "⧖ linear"),
                "reasoning": f"Path {i+1}: '{future_glyph}' derived via {qbit['state']} (↔ {len(entangled_glyphs)} ancestry links)"
            }

            # 🔴 Weak Prediction Feedback
            if prediction["confidence"] < 0.4:
                self.feedback_tracer.trace_feedback_path(prediction["id"], prediction, "Low confidence forecast")
                await self.gradient_engine._inject_gradient_feedback(prediction, "Low-confidence symbolic prediction")
                self.entanglement_adapter.propagate_gradient_feedback(prediction["id"], "Low-confidence bias")

                # 🌐 Multi-agent gradient sync
                await self.entanglement_fusion.propagate_gradient(
                    glyph_id=prediction["id"],
                    gradient_vector={"low_confidence": prediction["confidence"]},
                    source_agent=agent_id
                )

            # 🌌 Stream live node update
            await self.brain_streamer.stream_node_update(prediction["id"], status="neutral")

            predictions.append(prediction)

        # 🔻 Collapse feedback & recursive optimization
        collapsed = self.quantum_core.collapse_qbit(qbit)
        await self._inject_collapse_feedback(collapsed, current_glyph, goal, container_path, coord, agent_id=agent_id)

        # Store predictions in KG
        try:
            add_prediction_path({
                "input": current_glyph,
                "goal": goal,
                "paths": predictions,
                "qbit_state": collapsed,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "container_path": container_path,
                "coord": coord,
            })
        except Exception as e:
            print(f"⚠️ Prediction KG injection failed: {e}")

        self.history.extend(predictions)
        return predictions

    async def _inject_collapse_feedback(self, collapsed_qbit: dict, current_glyph: str, goal: str, container_path: str, coord: str, agent_id: str = "local"):
        """Handles collapse bias, streams ripples, triggers recursive re-predictions, and multi-agent sync."""
        try:
            if self.dream_core:
                self.dream_core.reflect_qglyph_collapse(collapsed_qbit)

            await self.gradient_engine.handle_qglyph_collapse(collapsed_qbit, agent_id=agent_id)
            self.entanglement_adapter.propagate_from_collapse(collapsed_qbit)

            qglyph_id = collapsed_qbit.get("selected", {}).get("qbit_id", "unknown")
            await self.entanglement_fusion.fuse_entangled_nodes(
                glyph_id=qglyph_id,
                confidence_delta=+0.05,
                source_agent=agent_id
            )

            await self.brain_streamer.stream_collapse_ripple(collapsed_qbit)

            bias_score = collapsed_qbit.get("observer_bias", {}).get("decision", 0)
            if abs(bias_score) > 0.6:
                print("🔁 Strong collapse bias detected -> triggering recursive re-prediction...")
                await self.generate_future_paths(current_glyph, container_path, goal, coord, agent_id=agent_id)

        except Exception as e:
            print(f"⚠️ Collapse feedback failed: {e}")

    # Remaining utility methods unchanged...
    def _predict_with_quantum(self, glyph, goal_vector, entangled, qbit):
        if qbit["state"] == "superposed":
            return f"{glyph} ⚛ ⧖ [superposed fork]"
        elif entangled:
            return f"{glyph} ↔ {random.choice(entangled)}"
        else:
            suffix = random.choice(["->", "⮕", "⋯", "⊕"])
            goal_hint = f"⟦{random.choice(['align','expand','mirror'])}⟧" if goal_vector else "?"
            return f"{glyph} {suffix} {goal_hint}"

    def _embed_goal(self, goal: Optional[str]) -> Optional[List[float]]:
        if not goal or not self.tessaris_engine:
            return None
        try:
            return self.tessaris_engine.embed_text(goal)
        except Exception:
            return None

    def _estimate_confidence(self, input_glyph: str, prediction: str, emotion: Optional[str], goal_vector: Optional[List[float]]) -> float:
        base = 0.5
        if emotion == "positive": base += 0.2
        elif emotion == "negative": base -= 0.2

        if goal_vector and self.tessaris_engine:
            try:
                pred_vector = self.tessaris_engine.embed_text(prediction)
                base += self._cosine_similarity(goal_vector, pred_vector) * 0.3
            except:
                pass

        if self.memory_engine:
            memories = self.memory_engine.search_similar_glyphs(input_glyph, top_k=3)
            if any(m["glyph"] in prediction for m in memories):
                base += 0.1

        return round(min(max(base, 0.0), 1.0), 2)

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a ** 2 for a in vec1))
        norm2 = math.sqrt(sum(b ** 2 for b in vec2))
        return dot / (norm1 * norm2 + 1e-8)

    def _check_soul_laws(self, glyph_text: str) -> Optional[Dict]:
        for law in get_soul_laws():
            for trigger in law.get("triggers", []):
                if trigger.lower() in glyph_text.lower():
                    return {"law_id": law["id"], "title": law["title"]}
        return None

    # ─────────────────────────────────────────────
    # 🌐 Compatibility Wrapper for Forecast API
    # ─────────────────────────────────────────────
    def forecast(self, query: str) -> dict:
        """
        Compatibility method for StrategyPlanner and Tessaris subsystems.
        Ensures a uniform interface, even if the core model uses different naming.
        """
        try:
            # Prefer an existing prediction method
            if hasattr(self, "predict"):
                result = self.predict(query)
            elif hasattr(self, "generate_prediction"):
                result = self.generate_prediction(query)
            else:
                # Fallback: simulated response
                result = {
                    "summary": f"Predicted outcome for '{query}'",
                    "confidence": 0.5
                }

            # Normalize the structure
            if isinstance(result, str):
                return {"summary": result, "confidence": 0.5}
            if isinstance(result, dict):
                result.setdefault("summary", "No summary available")
                result.setdefault("confidence", 0.5)
                return result

            return {"summary": str(result), "confidence": 0.5}

        except Exception as e:
            print(f"[PredictionEngine] ⚠️ forecast() failed: {e}")
            return {"summary": "⚠️ Forecast unavailable", "confidence": 0.0}

    def _matches_dream_trace(self, glyph_text: str) -> bool:
        if not self.dream_core:
            return False
        try:
            past_dreams = self.dream_core.get_recent_dreams(limit=5)
            return any(glyph_text in d.get("summary", "") for d in past_dreams)
        except:
            return False

    def summarize_prediction_trace(self) -> List[str]:
        return [f"{p['input_glyph']} -> {p['predicted_glyph']} ({p['confidence']})" for p in self.history]

    def reset_history(self):
        self.history.clear()

    # === SQI A2-A5: PredictionEngine for atoms/electrons with SoulLaw ===

    try:
        from backend.modules.soullaw.soul_law_validator import get_soul_laws
    except ImportError:
        get_soul_laws = lambda: []

    def _predict_atom(self, container: Dict[str, Any]) -> Dict[str, Any]:
        electrons = container.get("electrons", [])
        predictions = []

        for idx, electron in enumerate(electrons):
            label = electron.get("meta", {}).get("label", f"e- {idx+1}")
            glyphs = electron.get("glyphs", [])

            # ✅ A5: SoulLaw validation
            if not self._passes_soul_law(glyphs):
                logger.warning(f"⚠️ SoulLaw violation detected in electron: {label}")
                continue

            # ✅ A3: Confidence scoring
            best = max(glyphs, key=lambda g: g.get("confidence", 0), default=None)
            if best:
                predictions.append({
                    "electron": label,
                    "selected": best.get("value"),
                    "confidence": best.get("confidence"),
                    "linkContainerId": electron.get("meta", {}).get("linkContainerId", None)
                })

        return {
            "container_id": container.get("id"),
            "type": "atom",
            "prediction_count": len(predictions),
            "predictions": predictions
        }

    def _passes_soul_law(self, glyphs: List[Dict[str, Any]]) -> bool:
        for glyph in glyphs:
            for law in self.soul_laws:
                if not law.validate(glyph):
                    return False
        return True

# ✅ Singleton instance
_prediction_engine_instance = None

def get_prediction_engine():
    global _prediction_engine_instance
    if _prediction_engine_instance is None:
        _prediction_engine_instance = PredictionEngine()
    return _prediction_engine_instance

# ✅ Public wrapper for container-level prediction
def run_prediction_on_container(container: Dict[str, Any]) -> Dict[str, Any]:
    return get_prediction_engine().run_prediction_on_container(container)

# ✅ Public wrapper for AST-level prediction
def run_prediction_on_ast(ast_or_raw: dict) -> dict:
    return get_prediction_engine()._run_prediction_on_ast(ast_or_raw)

import random, logging
log = logging.getLogger(__name__)

def assess_feasibility(self, goal):
    """
    Returns a pseudo-probabilistic feasibility score (0-1)
    based on symbolic goal complexity and random harmonics.
    """
    if not goal:
        return 0.0

    goal_text = goal if isinstance(goal, str) else str(goal)
    complexity = min(len(goal_text) / 64.0, 1.0)  # heuristic: longer = harder
    base_resonance = 1.0 - (complexity * 0.5)
    noise = random.uniform(-0.1, 0.1)
    feasibility = max(0.0, min(1.0, base_resonance + noise))
    log.info(f"[PredictionEngine] Feasibility({goal_text}) = {feasibility:.3f}")
    return feasibility

# Attach dynamically if missing
try:
    if not hasattr(PredictionEngine, "assess_feasibility"):
        PredictionEngine.assess_feasibility = assess_feasibility
except NameError:
    pass

__all__ = [
    "run_prediction_on_container",
    "run_prediction_on_ast",
    "select_best_prediction"
]
from backend.modules.glyphwave.emit_beam import emit_qwave_beam as emit_qwave_beam_ff

# alias for compatibility with tests
emit_qwave_beam_ff = get_emit_qwave_beam_ff()