# ===============================
# 📁 backend/modules/codex/codex_virtual_qpu.py
# ===============================
"""
CodexVirtualQPU: Phase 7 QPU ISA Execution Layer

- Executes GlyphCell logic using symbolic QPU ISA
- Stubs for entanglement, collapse, superposition
- Integration hooks for SQS, SCI, QFC
- Metrics tracking & production-ready logging
- Instruction-level profiling (G3)
- FP4/FP8/INT8 symbolic simulation
"""
from typing import Any, Dict, List, Optional
from time import perf_counter
import asyncio
from uuid import uuid4

from backend.modules.codex.hardware.symbolic_qpu_isa import (
    execute_qpu_opcode,
    SYMBOLIC_QPU_OPS,
)
# Safe tokenizer import to avoid circulars during tests
try:
    from backend.modules.glyphos.glyph_tokenizer import tokenize_symbol_text_to_glyphs
except Exception:
    def tokenize_symbol_text_to_glyphs(s: str):
        return [{"type": "operator", "value": t} for t in (s or "").split()]

from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell
from backend.modules.patterns.pattern_trace_engine import record_trace
from backend.modules.visualization.qfc_websocket_bridge import broadcast_qfc_update
from backend.modules.utils.time_utils import now_utc_iso, now_utc_ms
from backend.modules.codex._4d_dreams import phase9_run

# --- Lazy SQI scorer to avoid circular imports during test collection/execution ---
def _score_sqi(cell) -> float:
    """
    Tries to import the real SQI scorer only when needed.
    Falls back to a simple heuristic if the scorer isn't available yet.
    """
    try:
        # Lazy import to dodge partial-init circulars
        from backend.modules.symbolic_spreadsheet.scoring.sqi_scorer import score_sqi as _impl
    except Exception:
        # Minimal fallback: base + small bonus for prediction forks
        logic = getattr(cell, "logic", "") or ""
        forks = len(getattr(cell, "prediction_forks", []) or [])
        base = 0.75 if logic else 0.5
        bonus = min(0.25, 0.05 * forks)
        try:
            return float(max(0.0, min(1.0, base + bonus)))
        except Exception:
            return 0.75

    # Use the real scorer
    try:
        return float(_impl(cell))
    except Exception:
        return 0.75

class CodexVirtualQPU:
    def __init__(self, use_qpu: bool = True):
        self.use_qpu: bool = use_qpu
        self.metrics_enabled: bool = True
        self.reset_metrics()
        self.opcode_metrics: Dict[str, Dict[str, Any]] = {}
        # NEW: per-op precision profiling accumulators
        self.precision_stats: Dict[str, Dict[str, float]] = {}  # {opcode: {...}}

    # -------------------
    # Metrics
    # -------------------
    def reset_metrics(self) -> None:
        self.metrics: Dict[str, float] = {
            "execution_time": 0.0,
            "sqi_shift": 0.0,
            "mutation_count": 0
        }
        self.token_metrics: Dict[str, List[float]] = {}
        # NEW: reset precision stats
        self.precision_stats: Dict[str, Dict[str, float]] = {}

    def dump_metrics(self) -> Dict[str, float]:
        """Return a shallow copy of aggregate QPU metrics."""
        return dict(self.metrics)        

    # In CodexVirtualQPU
    def to_fp4(self, x: float) -> float:
        # 16 bins across a small dynamic range
        # (simple symmetric quantizer for demo)
        scale = 8.0
        q = round(max(min(x, 1.0), -1.0) * scale) / scale
        return float(q)

    def to_fp8(self, x: float) -> float:
        # 256-ish levels (coarser than real FP8, but good for demo)
        scale = 128.0
        q = round(max(min(x, 2.0), -2.0) * scale) / scale
        return float(q)

    def to_int8(self, x: float) -> int:
        # Saturating int8 with unit scale for demo
        q = int(max(min(round(x * 100), 127), -127))
        return q

    # -------------------
    # G3 helpers: precision/error accumulation
    # -------------------
    def _accum_precision(
        self,
        opcode: str,
        baseline: float,
        fp4: float,
        fp8: float,
        int8: float,
        t_fp4: float,
        t_fp8: float,
        t_int8: float,
    ) -> None:
        import math
        def rel_err(approx: float, exact: float) -> float:
            denom = abs(exact) if exact else 1.0
            # guard against inf/nan
            if not (math.isfinite(approx) and math.isfinite(exact)):
                return 1.0
            return abs(approx - exact) / (abs(denom) + 1e-9)

        stats = self.precision_stats.setdefault(opcode, {
            "count": 0,
            "fp4_time": 0.0,  "fp8_time": 0.0,  "int8_time": 0.0,
            "fp4_rel_err": 0.0, "fp8_rel_err": 0.0, "int8_rel_err": 0.0,
            "fp4_abs_err": 0.0, "fp8_abs_err": 0.0, "int8_abs_err": 0.0,
        })
        stats["count"] += 1
        stats["fp4_time"] += t_fp4
        stats["fp8_time"] += t_fp8
        stats["int8_time"] += t_int8

        stats["fp4_abs_err"] += abs(fp4 - baseline)
        stats["fp8_abs_err"] += abs(fp8 - baseline)
        stats["int8_abs_err"] += abs(int8 - baseline)

        stats["fp4_rel_err"] += rel_err(fp4, baseline)
        stats["fp8_rel_err"] += rel_err(fp8, baseline)
        stats["int8_rel_err"] += rel_err(int8, baseline)

    def recommend_precision_for_opcode(
        self,
        opcode: str,
        rel_err_budget: float = 0.05  # 5% default budget
    ) -> str:
        stats = self.precision_stats.get(opcode)
        if not stats or stats["count"] == 0:
            return "fp8"  # safe default

        c = stats["count"]
        avg_time = {
            "fp4":  stats["fp4_time"] / c,
            "fp8":  stats["fp8_time"] / c,
            "int8": stats["int8_time"] / c,
        }
        avg_rel = {
            "fp4":  stats["fp4_rel_err"] / c,
            "fp8":  stats["fp8_rel_err"] / c,
            "int8": stats["int8_rel_err"] / c,
        }

        # Choose fastest that meets error budget; else pick lowest error
        candidates = [(avg_time[p], p) for p in ("fp4","fp8","int8") if avg_rel[p] <= rel_err_budget]
        if candidates:
            candidates.sort()
            return candidates[0][1]
        return min((avg_rel[p], p) for p in ("fp4","fp8","int8"))[1]

    def get_precision_profile(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for op, s in self.precision_stats.items():
            c = s.get("count", 0)
            if c <= 0: 
                continue
            out[op] = {
                "count": c,
                "avg_time": {
                    "fp4":  s["fp4_time"] / c,
                    "fp8":  s["fp8_time"] / c,
                    "int8": s["int8_time"] / c,
                },
                "avg_abs_err": {
                    "fp4":  s["fp4_abs_err"] / c,
                    "fp8":  s["fp8_abs_err"] / c,
                    "int8": s["int8_abs_err"] / c,
                },
                "avg_rel_err": {
                    "fp4":  s["fp4_rel_err"] / c,
                    "fp8":  s["fp8_rel_err"] / c,
                    "int8": s["int8_rel_err"] / c,
                },
                "recommendation": self.recommend_precision_for_opcode(op)
            }
        return out

    # -------------------
    # Stubs for quantum ops
    # -------------------
    def entangle_cells(self, cell_a: GlyphCell, cell_b: GlyphCell) -> bool:
        try:
            record_trace(cell_a.id, f"[QPU Stub] Entangling {cell_a.id} ↔ {cell_b.id}")
            self.metrics["mutation_count"] += 1
            return True
        except Exception as e:
            record_trace(cell_a.id, f"[QPU Error] Entangle failed: {e}")
            return False

    def collapse_cell(self, cell: GlyphCell) -> bool:
        try:
            record_trace(cell.id, f"[QPU Stub] Collapsing {cell.id}")
            self.metrics["mutation_count"] += 1
            return True
        except Exception as e:
            record_trace(cell.id, f"[QPU Error] Collapse failed: {e}")
            return False

    def superpose_cell(self, cell: GlyphCell) -> bool:
        try:
            record_trace(cell.id, f"[QPU Stub] Superposing {cell.id}")
            return True
        except Exception as e:
            record_trace(cell.id, f"[QPU Error] Superpose failed: {e}")
            return False

    # -------------------
    # Instruction-level execution w/ metrics
    # -------------------
    async def execute_cell_token(self, token: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """
        Execute a single token as a QPU instruction with metrics, FP simulation,
        SQI hooks, mutation counting, live HUD broadcasting, and per-cell QWave beam logging.

        Phase 8 addition:
        - If the token is ↔, tag the appended beam with a deterministic entanglement id (eid)
        and add the cell to context["entanglements_map"][eid].
        """
        context = context or {}
        cell: Optional[GlyphCell] = context.get("cell")
        start_time = perf_counter()

        token_key = token.get("value", "?")
        fp4_elapsed = fp8_elapsed = int8_elapsed = 0.0
        result: Any = None

        try:
            # Execute opcode
            result = execute_qpu_opcode(token_key, [token], cell, context)

            # -------------------
            # Track FP precision timings (and accumulate profile)
            # -------------------
            # ensure these always exist for the finally/token_metrics section
            fp4_elapsed = fp8_elapsed = int8_elapsed = 0.0

            if isinstance(result, (float, int)):
                # numeric baseline -> do real quantization timings
                baseline_val = float(result)

                fp4_start = perf_counter()
                result_fp4 = self.to_fp4(baseline_val)
                fp4_elapsed = perf_counter() - fp4_start

                fp8_start = perf_counter()
                result_fp8 = self.to_fp8(baseline_val)
                fp8_elapsed = perf_counter() - fp8_start

                int8_start = perf_counter()
                result_int8 = self.to_int8(baseline_val)
                int8_elapsed = perf_counter() - int8_start

                context["last_precision"] = {
                    "fp4": result_fp4,
                    "fp8": result_fp8,
                    "int8": result_int8
                }

                # accumulate per-op precision stats with real values
                try:
                    self._accum_precision(
                        opcode=token_key,
                        baseline=baseline_val,
                        fp4=float(result_fp4),
                        fp8=float(result_fp8),
                        int8=float(result_int8),
                        t_fp4=fp4_elapsed,
                        t_fp8=fp8_elapsed,
                        t_int8=int8_elapsed,
                    )
                except Exception as _e:
                    record_trace(token_key, f"[PrecisionProfile Warn] {_e}")

            else:
                # non-numeric result -> still create a placeholder sample
                # so the opcode appears in the precision profile.
                # We record zero timings & zero relative error.
                try:
                    self._accum_precision(
                        opcode=token_key,
                        baseline=0.0,
                        fp4=0.0,
                        fp8=0.0,
                        int8=0.0,
                        t_fp4=0.0,
                        t_fp8=0.0,
                        t_int8=0.0,
                    )
                except Exception as _e:
                    record_trace(token_key, f"[PrecisionProfile Warn] {_e}")

            # Count successful mutation/op execution
            self.metrics["mutation_count"] += 1

        except Exception as e:
            result = f"[QPU ERROR {token_key}: {str(e)}]"

        finally:
            # Always track total execution
            total_elapsed = perf_counter() - start_time
            self.metrics["execution_time"] += total_elapsed

            # Record per-token metrics exactly once
            self.token_metrics.setdefault(token_key, []).append({
                "total": total_elapsed,
                "fp4": fp4_elapsed,
                "fp8": fp8_elapsed,
                "int8": int8_elapsed
            })

            # Per-cell opcode breakdown
            if cell and getattr(cell, "id", None):
                stats = self.opcode_metrics.setdefault(cell.id, {}).setdefault(token_key, {
                    "count": 0,
                    "total_time": 0.0,
                    "fp4_time": 0.0,
                    "fp8_time": 0.0,
                    "int8_time": 0.0
                })
                stats["count"] += 1
                stats["total_time"] += total_elapsed
                stats["fp4_time"] += fp4_elapsed
                stats["fp8_time"] += fp8_elapsed
                stats["int8_time"] += int8_elapsed

            record_trace(token_key, f"[Token Metrics] exec_time={total_elapsed:.6f}s")

        # -------------------
        # Append QWave beam to cell (integration) + Phase 8 entanglement tagging
        # -------------------
        if cell is not None:
            # Ensure attribute exists
            if not hasattr(cell, "wave_beams") or cell.wave_beams is None:
                cell.wave_beams = []

            # Phase 8: if this is ↔, compute deterministic entanglement id (eid)
            entanglement_ids: List[str] = []
            if token_key == "↔":
                sheet_run_id = context.get("sheet_run_id", "run")
                logic_hash = abs(hash(getattr(cell, "logic", "") or "")) % (2**32)
                eid = f"eid::{sheet_run_id}::{logic_hash}"
                entanglement_ids = [eid]

                # ensure context entanglement map includes this cell
                ent_map = context.setdefault("entanglements_map", {})  # eid -> set(cell_ids)
                ent_map.setdefault(eid, set()).add(cell.id)

            beam_event = {
                "beam_id": f"beam_{cell.id}_{token_key}_{now_utc_ms()}",
                "source": "qpu_execute_token",
                "token": token_key,
                "result": result,
                "timestamp": now_utc_iso(),
                "state": "mutated" if getattr(cell, "mutation_score", None) else "active",
                "stage": "ingest",  # Phase 8: ensures tests can see the ingest stage
                "entanglement_ids": entanglement_ids,  # Phase 8: tag ↔ beams with eid
                "context": context,
            }
            cell.wave_beams.append(beam_event)

        # -------------------
        # Async broadcast metrics for HUD (gated)
        # -------------------
        should_broadcast = ("container_id" in context) and not context.get("benchmark_silent")
        if should_broadcast and cell and getattr(cell, "id", None):
            try:
                import asyncio
                asyncio.create_task(broadcast_qfc_update(context["container_id"], {
                    "type": "qpu_cell_update",
                    "cell_id": cell.id,
                    "sqi": getattr(cell, "sqi_score", 0.0),
                    "mutation_count": self.metrics.get("mutation_count", 0),
                    "exec_time": total_elapsed,
                    "token_metrics": self.token_metrics.get(cell.logic, []),
                    "opcode_breakdown": self.opcode_metrics.get(cell.id, {})
                }))
            except Exception as e:
                record_trace(cell.id, f"[QPU Broadcast Error] {e}")

        return result


    # -------------------
    # Integration Hooks
    # -------------------
    def hook_to_sqs_engine(self, cell: GlyphCell, context: Dict[str, Any]) -> None:
        context["sqi_update"] = cell.sqi_score
        record_trace(cell.id, f"[QPU Hook] SQI updated: {cell.sqi_score}")

    def broadcast_to_qfc(self, cell: GlyphCell, container_id: str) -> None:
        try:
            broadcast_qfc_update(container_id, {
                "type": "qpu_update",
                "cell_id": cell.id,
                "sqi": cell.sqi_score
            })
            record_trace(cell.id, f"[QPU Hook] Broadcasted to QFC container {container_id}")
        except Exception as e:
            record_trace(cell.id, f"[QPU Error] Broadcast failed: {e}")


    # -------------------
    # Execute single cell (async)
    # -------------------
    async def execute_cell(
        self,
        cell: GlyphCell,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        import asyncio

        context = context or {}
        context.setdefault("entangled_cells", [])
        context["cell"] = cell  # ensure token executor can read the current cell
        setattr(cell, "_ctx", context)

        # Ensure attributes exist
        cell.prediction_forks = getattr(cell, "prediction_forks", [])
        cell.wave_beams = getattr(cell, "wave_beams", [])

        if not self.use_qpu:
            record_trace(cell.id, "[QPU Disabled] Skipping execution")
            return []

        start_time = perf_counter()
        results: List[Any] = []

        try:
            tokens = tokenize_symbol_text_to_glyphs(cell.logic)
            for token in tokens:
                try:
                    value = token["value"]
                    if value in SYMBOLIC_QPU_OPS:
                        res = await self.execute_cell_token(token, context=context)
                        results.append(res)
                        record_trace(cell.id, f"[QPU Executed] {value}: {res}")
                    else:
                        results.append(f"[Literal {value}]")
                        record_trace(cell.id, f"[QPU Literal] {value}")
                except Exception as e:
                    record_trace(cell.id, f"[QPU Error] Token '{token.get('value', '?')}' failed: {e}")
                    results.append(f"[Error {token.get('value', '?')}]")

            prev_sqi = float(getattr(cell, "sqi_score", 0.0) or 0.0)
            cell.sqi_score = _score_sqi(cell)
            self.metrics["sqi_shift"] += cell.sqi_score - prev_sqi

            # --- Append final QWave beam for the entire cell execution ---
            final_beam = {
                "beam_id": f"beam_{cell.id}_final_{now_utc_ms()}",
                "source": "qpu_execute_cell",
                "result": results,
                "sqi_score": cell.sqi_score,
                "timestamp": now_utc_iso(),
                "state": "collapsed",
                "context": context,
            }
            cell.wave_beams.append(final_beam)
            cell.wave_beams.append(final_beam)

            self.hook_to_sqs_engine(cell, context)

            # Async broadcast (respect benchmark_silent flag)
            should_broadcast = ("container_id" in context) and not context.get("benchmark_silent")
            if should_broadcast and cell.id:
                try:
                    asyncio.create_task(
                        broadcast_qfc_update(context["container_id"], {
                            "type": "qpu_cell_update",
                            "cell_id": cell.id,
                            "sqi": cell.sqi_score,
                            "mutation_count": self.metrics["mutation_count"],
                            "exec_time": perf_counter() - start_time,
                            "token_metrics": self.token_metrics.get(cell.logic, []),
                            "opcode_breakdown": self.opcode_metrics.get(cell.id, {})
                        })
                    )
                except Exception as e:
                    record_trace(cell.id, f"[QPU Broadcast Error] {e}")

        finally:
            elapsed = perf_counter() - start_time
            self.metrics["execution_time"] += elapsed
            record_trace(cell.id, f"[QPU Metrics] exec_time={elapsed:.6f}s")

        return results

    # -------------------
    # Execute full sheet (async)
    # -------------------
    def _score_sqi_lazy(self, cell) -> float:
        try:
            from backend.modules.symbolic_spreadsheet.scoring.sqi_scorer import score_sqi as _score_sqi
            return float(_score_sqi(cell))
        except Exception as e:
            record_trace("SQI:Init", f"Lazy import fallback for score_sqi: {e}")
            return float(getattr(cell, "sqi_score", 1.0) or 1.0)

    def _compute_sheet_sqi(self, cells, context) -> float:
        scores = []
        for c in cells:
            s = self._score_sqi_lazy(c)
            setattr(c, "sqi_score", s)
            scores.append(s)
        sheet_sqi = sum(scores) / max(1, len(scores))
        context["sheet_sqi"] = sheet_sqi
        return sheet_sqi

    # --- Phase 8: sheet executor (bounded parallelism + beams + entanglement map) ---
    async def execute_sheet(
        self,
        cells: List[GlyphCell],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[Any]]:
        import asyncio
        from time import perf_counter
        from uuid import uuid4
        from datetime import datetime, UTC

        try:
            from backend.modules.glyphos.glyph_tokenizer import tokenize_symbol_text_to_glyphs
        except Exception:
            def tokenize_symbol_text_to_glyphs(s: str):
                return [{"type": "operator", "value": t} for t in (s or "").split()]

        context = context or {}
        context["sheet_cells"] = cells
        context["sheet_run_id"] = context.get("sheet_run_id") or uuid4().hex[:8]
        context.setdefault("entanglements_map", {})  # eid -> set(cell_ids)

        sheet_results: Dict[str, List[Any]] = {}
        start_time = perf_counter()

        # ------ Bounded parallelism ------
        max_conc = int(context.get("max_concurrency", 1) or 1)
        if max_conc <= 1:
            for cell in cells:
                sheet_results[cell.id] = await self.execute_cell(cell, context)
        else:
            sem = asyncio.Semaphore(max_conc)
            async def run_cell(c: GlyphCell):
                async with sem:
                    res = await self.execute_cell(c, context)
                    sheet_results[c.id] = res
            await asyncio.gather(*(run_cell(c) for c in cells))

        # ------ Optional batched collapse hook ------
        if context.get("batch_collapse"):
            try:
                sheet_sqi = self._compute_sheet_sqi(cells, context)
                # add a sheet-level collapse beam to each cell for timeline rendering
                for cell in cells:
                    if not hasattr(cell, "wave_beams") or cell.wave_beams is None:
                        cell.wave_beams = []
                    cell.wave_beams.append({
                        "beam_id": f"beam_{cell.id}_final_{now_utc_ms()}",
                        "source": "qpu_sheet_batch_collapse",
                        "stage": "collapse",
                        "token": "∑",
                        "result": {"sheet_sqi": sheet_sqi},
                        "timestamp": now_utc_iso(),
                        "entanglement_ids": list((context.get("entanglements_map") or {}).keys())[:1] or [],
                    })
            except Exception as _e:
                record_trace("sheet", f"[BatchCollapse Warn] {_e}")

        # ------ Aggregate metrics ------
        sheet_token_metrics: Dict[str, Dict[str, List[Any]]] = {}
        for cell in cells:
            try:
                tokens = tokenize_symbol_text_to_glyphs(cell.logic or "")
                keys = {t.get("value") for t in tokens if "value" in t}
            except Exception:
                keys = set()
            sheet_token_metrics[cell.id] = {k: self.token_metrics.get(k, []) for k in keys}

        sheet_opcode_metrics = {cell.id: self.opcode_metrics.get(cell.id, {}) for cell in cells}

        record_trace("sheet", f"[QPU Sheet Metrics] {self.dump_metrics()}")
        record_trace("sheet", f"[QPU Sheet Token Metrics] {sheet_token_metrics}")
        record_trace("sheet", f"[QPU Sheet Opcode Metrics] {sheet_opcode_metrics}")

        # ------ Build entanglement map (eid -> [cell_ids]) ------
        ent_map: Dict[str, List[str]] = {}
        # merge context map (from ↔) and beams
        ctx_map = context.get("entanglements_map", {})
        for eid, cid_set in ctx_map.items():
            ent_map[eid] = sorted(list(cid_set))
        # sweep beams to catch directly annotated entanglements
        for c in cells:
            for b in (getattr(c, "wave_beams", []) or []):
                for eid in b.get("entanglement_ids", []):
                    ent_map.setdefault(eid, [])
                    if c.id not in ent_map[eid]:
                        ent_map[eid].append(c.id)
        for eid in ent_map:
            ent_map[eid] = sorted(ent_map[eid])

        # ------ Phase 9: Dream projection + timeline snapshot (optional) ------
        if context.get("phase9_enabled"):
            try:
                from backend.modules.codex._4d_dreams import phase9_run
                phase9 = phase9_run(
                    cells,
                    context,
                    k_variants=int(context.get("phase9_k", 3) or 3),
                    min_sqi_keep=float(context.get("phase9_min_sqi", 0.60) or 0.60),
                    stage_name=str(context.get("phase9_stage", "dream") or "dream"),
                )
                # stash for broadcast
                context["phase9_payload"] = phase9
            except Exception as _e:
                record_trace("sheet", f"[Phase9 Warn] {str(_e)}")

        # ------ Phase 10: Vectorized kernels + precision (optional) ------
        if context.get("phase10_enabled"):
            try:
                from backend.modules.codex.accel import phase10_accelerate_sheet
                p10 = phase10_accelerate_sheet(cells, context)
                context["phase10_summary"] = p10
            except Exception as _e:
                record_trace("sheet", f"[Phase10 Warn] {str(_e)}")

        # ------ QFC container-level execution (optional) ------
        if context.get("qfc_container_batch"):
            try:
                from backend.modules.codex.container_exec import execute_qfc_container_beams
                p10c = execute_qfc_container_beams(
                    context.get("container_id"),
                    cells,
                    context["qfc_container_batch"],
                    context
                )
                context["phase10_container_exec"] = p10c
            except Exception as _e:
                record_trace("sheet", f"[Phase10/QFC Warn] {str(_e)}")

        # ------ Persist beams & entanglements + ghost replay (after P9/P10) ------
        try:
            from backend.modules.beamline.beam_store import persist_beam_events, ghost_replay_for_eid
            persist_beam_events(cells, context)
            context.setdefault("ghost_replays", {})
            for eid in ent_map.keys():
                try:
                    context["ghost_replays"][eid] = ghost_replay_for_eid(
                        eid, limit=3, container_id=context.get("container_id")
                    )
                except Exception:
                    pass
        except Exception as _e:
            record_trace("sheet", f"[BeamStore Persist Warn] {_e}")

        # ------ Broadcasts (gated by benchmark_silent) ------
        should_broadcast = ("container_id" in context) and not context.get("benchmark_silent")
        if should_broadcast:
            try:
                import asyncio
                from datetime import datetime, UTC

                wsid = context.get("workspace_id")
                base = (
                    {"workspace_id": wsid, "sheet_run_id": context["sheet_run_id"]}
                    if wsid else {"sheet_run_id": context["sheet_run_id"]}
                )

                # Build once so all payloads are consistent
                lineage_payload = {c.id: (getattr(c, "wave_beams", []) or []) for c in cells}

                # 1) sheet metrics
                asyncio.create_task(
                    broadcast_qfc_update(context["container_id"], {
                        **base,
                        "type": "qpu_sheet_metrics",
                        "sheet_token_metrics": sheet_token_metrics,
                        "sheet_opcode_metrics": sheet_opcode_metrics,
                        "aggregate_metrics": self.dump_metrics(),
                        "num_beams": sum(len(v) for v in lineage_payload.values()),
                        "num_entanglements": len(ent_map),
                    })
                )

                # 2) precision profile snapshot
                asyncio.create_task(
                    broadcast_qfc_update(context["container_id"], {
                        **base,
                        "type": "qpu_precision_profile",
                        "profile": self.get_precision_profile(),
                    })
                )

                # 3) beam lineage per cell
                asyncio.create_task(
                    broadcast_qfc_update(context["container_id"], {
                        **base,
                        "type": "qpu_beam_lineage",
                        "lineage": lineage_payload,
                    })
                )

                # 4) entanglement map
                asyncio.create_task(
                    broadcast_qfc_update(context["container_id"], {
                        **base,
                        "type": "qpu_entanglement_map",
                        "map": ent_map,
                    })
                )

                # 5) flat beam timeline snapshot
                flat_timeline = []
                for cid, beams in lineage_payload.items():
                    for b in beams:
                        ts = b.get("timestamp") or datetime.now(UTC).isoformat()
                        flat_timeline.append({
                            "cell_id": cid,
                            "beam_id": b.get("beam_id"),
                            "stage": b.get("stage"),
                            "eid": (b.get("entanglement_ids") or [None])[0],
                            "token": b.get("token"),
                            "timestamp": ts,
                        })
                asyncio.create_task(
                    broadcast_qfc_update(context["container_id"], {
                        **base,
                        "type": "qpu_beam_timeline",
                        "timeline": flat_timeline,
                    })
                )

                # 6) Phase 10 vectorized summary (if present)
                if context.get("phase10_summary"):
                    asyncio.create_task(
                        broadcast_qfc_update(context["container_id"], {
                            **base,
                            "type": "qpu_phase10_vectorized",
                            "summary": context["phase10_summary"],
                            "precision": str(context.get("phase10_precision", "fp8")),
                        })
                    )

                # 7) Phase 9 dreams/timeline (if present)
                if context.get("phase9_payload"):
                    p9 = context["phase9_payload"]
                    asyncio.create_task(
                        broadcast_qfc_update(context["container_id"], {
                            **base,
                            "type": "qpu_phase9_dreams",
                            "dreams": p9.get("dreams", {}),
                        })
                    )
                    asyncio.create_task(
                        broadcast_qfc_update(context["container_id"], {
                            **base,
                            "type": "qpu_phase9_timeline",
                            "timeline": p9.get("timeline", []),
                        })
                    )

                # 7) container-level execution summary (if present)
                if context.get("phase10_container_exec"):
                    asyncio.create_task(
                        broadcast_qfc_update(context["container_id"], {
                            **base,
                            "type": "qpu_container_exec",
                            "summary": context["phase10_container_exec"],
                        })
                    )

            except Exception as e:
                record_trace("sheet", f"[QPU Sheet Broadcast Error] {e}")

        elapsed = perf_counter() - start_time
        record_trace("sheet", f"[Sheet Execution] elapsed={elapsed:.6f}s")
        return sheet_results

    def merge_entanglement_context(self, ctx_a: dict, ctx_b: dict) -> dict:
        """Union two contexts' entanglement maps (multi-agent / multi-sheet)."""
        try:
            from backend.modules.beamline.beam_store import merge_entanglements
        except Exception:
            def merge_entanglements(a, b): 
                out = {k: set(v) for k, v in (a or {}).items()}
                for eid, members in (b or {}).items():
                    out.setdefault(eid, set()).update(set(members))
                return out
        merged = dict(ctx_a or {})
        merged["entanglements_map"] = merge_entanglements(
            ctx_a.get("entanglements_map", {}),
            ctx_b.get("entanglements_map", {})
        )
        return merged


    try:
        # Persist beams + entanglements
        from backend.modules.beamline.beam_store import persist_beam_events, ghost_replay_for_eid
        persist_beam_events(cells, context)

        # Optional: attach ghost replays for each eid to context (most recent 3)
        context.setdefault("ghost_replays", {})
        for eid in ent_map.keys():
            try:
                context["ghost_replays"][eid] = ghost_replay_for_eid(
                    eid, limit=3, container_id=context.get("container_id")
                )
            except Exception:
                pass
    except Exception as _e:
        record_trace("sheet", f"[BeamStore Persist Warn] {_e}")

# -------------------
# Standalone CLI Test
# -------------------
if __name__ == "__main__":
    import asyncio
    from backend.modules.symbolic_spreadsheet.models.glyph_cell import GlyphCell

    async def _main():
        # Example test GlyphCell
        test_cell = GlyphCell(
            id="cell_001",
            logic="⊕ ↔ ⟲ -> ✦",
            position=[0, 0],
            emotion="curious",
            prediction="Initial",
            wave_beams=[]
        )

        qpu = CodexVirtualQPU()

        print("\n💡 Executing single cell on QPU...")
        result = await qpu.execute_cell(test_cell, context={"container_id": "default_container"})
        print("Execution Result:", result)
        print("Prediction Forks:", test_cell.prediction_forks)
        print("SQI Score:", test_cell.sqi_score)
        print("QPU Metrics:", qpu.dump_metrics())

        print("\n💡 Executing a small sheet of 3 cells on QPU...")
        sheet = [
            GlyphCell(id=f"cell_{i}", logic="⊕ ↔ ⟲ -> ✦", position=[i, 0], wave_beams=[])
            for i in range(3)
        ]
        sheet_results = await qpu.execute_sheet(sheet, context={"container_id": "default_container"})
        print("Sheet Results:", sheet_results)
        print("Sheet Metrics:", qpu.dump_metrics())

        print("\n✅ QPU standalone test complete.")

    asyncio.run(_main())