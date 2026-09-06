"""Measured inference infrastructure for the AION adaptive runtime."""

from .baseline import (
    BenchmarkReport,
    BenchmarkResult,
    OllamaStreamingClient,
    WorkloadCase,
    benchmark_storage,
    collect_machine_inventory,
    collect_model_store_evidence,
    load_workloads,
    run_baseline,
)
from .semantic_gateway import GatewayResult, MeaningCapsule, SemanticGateway
from .verified_calculations import VerifiedCalculationResult, VerifiedCalculationRouter
from .adaptive_runtime import (
    AdaptiveInferenceRuntime,
    AdaptiveRuntimeResult,
    ContextSelection,
    ContextSelector,
    ReplayStore,
    verify_proof_receipt,
    verify_trace_chain,
)
from .learned_atomsheets import (
    LearnedAtomSheetStore,
    LearnedExecutionResult,
    LearningDecision,
    VerifiedModelOutcome,
)
from .glyph_context import GlyphContextDictionary, GlyphContextPacket, GlyphContextPassage
from .shard_selection import AddressedShard, AddressedShardExperiment, ShardReadMeasurement
from .sqi_beams import (
    ModelRoutePrediction,
    ModelRoutePredictor,
    RouteCollapse,
    SQICandidateBeam,
    WorkflowCatalog,
    WorkflowMatch,
    collapse_beams,
    collapse_beams_cost_aware,
    fuse_equivalent_beams,
)
from .expert_prefetch import (
    ExpertPrefetchPlan,
    PROFILE_DOMAINS,
    broad_expert_prefetch_plan,
    build_expert_prefetch_plan,
)
from .expert_cache_budget import (
    ExpertCacheBudgetPlan,
    ExpertCacheMemoryPlan,
    optimize_expert_cache_budget,
    optimize_expert_cache_memory_budget,
    simulate_frequency_cache_demand_bytes,
    verify_promoted_expert_cache_plan,
)
from .expert_route_corpus import ExpertRouteCorpus
from .expert_route_predictor import (
    build_cross_layer_route_capsule,
    predict_cross_layer_experts,
    verify_cross_layer_route_capsule,
)
from .expert_working_set import (
    build_expert_working_set_dictionary,
    select_predictive_retention,
    verify_expert_working_set_dictionary,
)
from .task_model_router import TaskModelRoute, select_task_model, verify_task_model_route

__all__ = [
    "BenchmarkReport",
    "BenchmarkResult",
    "OllamaStreamingClient",
    "WorkloadCase",
    "benchmark_storage",
    "collect_machine_inventory",
    "collect_model_store_evidence",
    "load_workloads",
    "run_baseline",
    "GatewayResult",
    "MeaningCapsule",
    "SemanticGateway",
    "VerifiedCalculationResult",
    "VerifiedCalculationRouter",
    "AdaptiveInferenceRuntime",
    "AdaptiveRuntimeResult",
    "ContextSelection",
    "ContextSelector",
    "ReplayStore",
    "verify_proof_receipt",
    "verify_trace_chain",
    "LearnedAtomSheetStore",
    "LearnedExecutionResult",
    "LearningDecision",
    "VerifiedModelOutcome",
    "GlyphContextDictionary",
    "GlyphContextPacket",
    "GlyphContextPassage",
    "AddressedShard",
    "AddressedShardExperiment",
    "ShardReadMeasurement",
    "ModelRoutePrediction",
    "ModelRoutePredictor",
    "RouteCollapse",
    "SQICandidateBeam",
    "WorkflowCatalog",
    "WorkflowMatch",
    "collapse_beams",
    "collapse_beams_cost_aware",
    "fuse_equivalent_beams",
    "ExpertPrefetchPlan",
    "PROFILE_DOMAINS",
    "broad_expert_prefetch_plan",
    "build_expert_prefetch_plan",
    "ExpertCacheBudgetPlan",
    "ExpertCacheMemoryPlan",
    "optimize_expert_cache_budget",
    "optimize_expert_cache_memory_budget",
    "simulate_frequency_cache_demand_bytes",
    "verify_promoted_expert_cache_plan",
    "ExpertRouteCorpus",
    "build_cross_layer_route_capsule",
    "predict_cross_layer_experts",
    "verify_cross_layer_route_capsule",
    "build_expert_working_set_dictionary",
    "select_predictive_retention",
    "verify_expert_working_set_dictionary",
    "TaskModelRoute",
    "select_task_model",
    "verify_task_model_route",
]
