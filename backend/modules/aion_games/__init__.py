from .general_game_adapter import (
    AionGeneralGameAdapter,
    AdaptedGameAction,
    AdaptedGameThreat,
    AdaptedGameState,
    GeneralGameAdapterResult,
    run_general_game_adapter,
)

__all__ = [
    "AionGeneralGameAdapter",
    "AdaptedGameAction",
    "AdaptedGameThreat",
    "AdaptedGameState",
    "GeneralGameAdapterResult",
    "run_general_game_adapter",
    "AionChessLikeThreatPlanner",
    "ChessThreatLine",
    "ChessActionEvaluation",
    "ChessLikeThreatPlanningResult",
    "run_chess_like_threat_planner",
    "AionMiniChessLegalMoveKernel",
    "MiniChessPiece",
    "MiniChessMove",
    "MiniChessLegalMoveResult",
    "run_mini_chess_legal_move_kernel",
    "AionMiniChessThreatMapKernel",
    "MiniThreatPiece",
    "MiniThreatMove",
    "MiniChessThreatMapResult",
    "run_mini_chess_threat_map_kernel",
    "AionMiniChessCaptureMaterialLearningKernel",
    "CaptureCandidate",
    "MiniChessCaptureMaterialLearningResult",
    "run_mini_chess_capture_material_learning_kernel",
    "AionMiniChessSelfPlayLearningKernel",
    "MiniChessGameEpisode",
    "MiniChessSelfPlayLearningResult",
    "run_mini_chess_self_play_learning_kernel",
    "AionMiniChessOpponentWinKernel",
    "OpponentGameTurn",
    "MiniChessOpponentWinResult",
    "run_mini_chess_opponent_win_kernel",
    "AionMiniChessFullLoopLock",
    "MiniChessFullLoopResult",
    "run_mini_chess_full_loop_lock",
    "AionFullChessBoardAdapterKernel",
    "FullChessPiece",
    "FullChessMove",
    "FullChessBoardAdapterResult",
    "run_full_chess_board_adapter_kernel",
    "AionFullChessMoveGeneratorKernel",
    "ChessPiece",
    "ChessMove",
    "FullChessMoveGeneratorResult",
    "run_full_chess_move_generator_kernel",
    "AionFullChessThreatMapKernel",
    "ThreatPiece",
    "ThreatMove",
    "FullChessThreatMapResult",
    "run_full_chess_threat_map_kernel",
    "AionFullChessLegalMoveSafetyKernel",
    "SafetyPiece",
    "SafetyMove",
    "FullChessLegalMoveSafetyResult",
    "run_full_chess_legal_move_safety_kernel",
    "AionFullChessCaptureEvaluationKernel",
    "CapturePiece",
    "FullChessCaptureEvaluationResult",
    "run_full_chess_capture_evaluation_kernel",
    "AionFullChessOpponentReplyKernel",
    "AionCandidateMove",
    "FullChessOpponentReplyResult",
    "run_full_chess_opponent_reply_kernel",
    "AionFullChessOnePlyStrategyKernel",
    "OnePlyCandidate",
    "FullChessOnePlyStrategyResult",
    "run_full_chess_one_ply_strategy_kernel",
    "AionFullChessMultiPlyLookaheadKernel",
    "LookaheadLine",
    "FullChessMultiPlyLookaheadResult",
    "run_full_chess_multi_ply_lookahead_kernel",
    "AionFullChessGameLoopKernel",
    "GameLoopTurn",
    "FullChessGameLoopResult",
    "run_full_chess_game_loop_kernel",
    "AionFullChessLearningLoopKernel",
    "LearningSignal",
    "FullChessLearningLoopResult",
    "run_full_chess_learning_loop_kernel",
    "AionFullChessSelfPlayImprovementKernel",
    "SelfPlayEpisode",
    "FullChessSelfPlayImprovementResult",
    "run_full_chess_self_play_improvement_kernel",
    "AionFullChessSelfPlayTournamentKernel",
    "TournamentPolicy",
    "TournamentMatch",
    "FullChessSelfPlayTournamentResult",
    "run_full_chess_self_play_tournament_kernel",
    "AionFullChessTournamentLearningIntegrationKernel",
    "TournamentLearningUpdate",
    "FullChessTournamentLearningIntegrationResult",
    "run_full_chess_tournament_learning_integration_kernel",
    "AionFullChessBoardStateMutationKernel",
    "BoardMutationMove",
    "FullChessBoardStateMutationResult",
    "run_full_chess_board_state_mutation_kernel",
    "AionFullLegalChessRulesKernel",
    "LegalRuleCase",
    "FullLegalChessRulesResult",
    "run_full_legal_chess_rules_kernel",
    "AionFullChessIoInterfaceKernel",
    "UciMove",
    "PgnRecord",
    "FullChessIoInterfaceResult",
    "run_full_chess_io_interface_kernel",
    "AionFullChessRealOpponentGameLoopKernel",
    "RealOpponentTurn",
    "FullChessRealOpponentGameLoopResult",
    "run_full_chess_real_opponent_game_loop_kernel",
    "AionFullChessBasicSearchEngineKernel",
    "SearchCandidate",
    "FullChessBasicSearchEngineResult",
    "run_full_chess_basic_search_engine_kernel",
    "AionFullChessSelfPlayTrainingKernel",
    "TrainingGame",
    "FullChessSelfPlayTrainingResult",
    "run_full_chess_self_play_training_kernel",
    "AionFullChessRatingBenchmarkKernel",
    "BenchmarkMatch",
    "FullChessRatingBenchmarkResult",
    "run_full_chess_rating_benchmark_kernel",
    "AionFullChessPlayableUiKernel",
    "UiMoveEntry",
    "PlayableUiState",
    "FullChessPlayableUiResult",
    "run_full_chess_playable_ui_kernel",
    "AionFullChessUciEngineWrapperKernel",
    "UciCommandTrace",
    "FullChessUciEngineWrapperResult",
    "run_full_chess_uci_engine_wrapper_kernel",
    "AionFullChessLichessBotBridgeKernel",
    "LichessBridgeEvent",
    "LichessMovePayload",
    "FullChessLichessBotBridgeResult",
    "run_full_chess_lichess_bot_bridge_kernel",
    "AionFullChessLiveLichessBotConnectorKernel",
    "LichessConnectorConfig",
    "LichessEndpointContract",
    "FullChessLiveLichessBotConnectorResult",
    "run_full_chess_live_lichess_bot_connector_kernel",
    "AionFullChessGuardedLiveMoveExecutionKernel",
    "GuardedLiveMoveRequest",
    "GuardDecision",
    "FullChessGuardedLiveMoveExecutionResult",
    "run_full_chess_guarded_live_move_execution_kernel",
    "AionFullChessAutonomousBotLearningPolicyKernel",
    "AutonomousLearningGame",
    "FullChessAutonomousBotLearningPolicyResult",
    "run_full_chess_autonomous_bot_learning_policy_kernel",
    "AionFullChessRealGameResultLearningLoopKernel",
    "RealGameResult",
    "RealGameLearningUpdate",
    "FullChessRealGameResultLearningLoopResult",
    "run_full_chess_real_game_result_learning_loop_kernel",
    "AionFullChessKnowledgeOpeningsStrategyBookKernel",
    "ChessKnowledgeEntry",
    "ChessKnowledgeQuery",
    "FullChessKnowledgeOpeningsStrategyBookResult",
    "run_full_chess_knowledge_openings_strategy_book_kernel",
    "AionFullChessKnowledgeGuidedMoveSelectionKernel",
    "CandidateMoveScore",
    "FullChessKnowledgeGuidedMoveSelectionResult",
    "run_full_chess_knowledge_guided_move_selection_kernel",
    "AionFullChessLocalEngineMatchHarnessKernel",
    "LocalOpponentProfile",
    "LocalMatchRecord",
    "FullChessLocalEngineMatchHarnessResult",
    "run_full_chess_local_engine_match_harness_kernel",
    "AionFullChessLocalTournamentRatingLadderKernel",
    "LadderTierResult",
    "FullChessLocalTournamentRatingLadderResult",
    "run_full_chess_local_tournament_rating_ladder_kernel",
    "AionFullChessLichessDryRunGameReplayKernel",
    "LichessReplayEvent",
    "DryRunReplayDecision",
    "FullChessLichessDryRunGameReplayResult",
    "run_full_chess_lichess_dry_run_game_replay_kernel",
    "AionFullChessLiveLichessBotEnablementKernel",
    "LiveLichessBotEnablementConfig",
    "LiveLichessBotEnablementDecision",
    "FullChessLiveLichessBotEnablementResult",
    "run_full_chess_live_lichess_bot_enablement_kernel",
    "AionFullChessRealLichessNetworkMoveSenderKernel",
    "RealLichessMoveSendRequest",
    "RealLichessMoveSendResult",
    "run_full_chess_real_lichess_network_move_sender_kernel",
    "AionFullChessLiveLichessGameLoopResultRecorderKernel",
    "LiveLichessGameLoopMoveRecord",
    "FullChessLiveLichessGameLoopResult",
    "run_full_chess_live_lichess_game_loop_result_recorder_kernel",
    "AionFullChessPostGameBlunderReviewKernel",
    "PostGameMoveReview",
    "FullChessPostGameBlunderReviewResult",
    "run_full_chess_post_game_blunder_review_kernel",
    "AionFullChessRealEvaluationFunctionKernel",
    "RealChessEvaluationBreakdown",
    "RealChessEvaluationResult",
    "run_full_chess_real_evaluation_function_kernel",
    "AionFullChessEvaluationGuidedMoveSelectionKernel",
    "EvaluationGuidedCandidateMove",
    "EvaluationGuidedMoveSelectionResult",
    "run_full_chess_evaluation_guided_move_selection_kernel",
    "AionFullChessDepthLimitedLookaheadSearchKernel",
    "DepthLimitedSearchCandidate",
    "DepthLimitedLookaheadSearchResult",
    "run_full_chess_depth_limited_lookahead_search_kernel",
    "AionFullChessLiveLoopSearchSelectorAdapterKernel",
    "LiveLoopSearchSelectorAdapterResult",
    "run_full_chess_live_loop_search_selector_adapter_kernel",
    "AionFullChessLiveLichessAutoplayV2Level2Kernel",
    "LiveLichessAutoplayV2Level2Result",
    "run_full_chess_live_lichess_autoplay_v2_level2_kernel",
    "AionFullChessSQIEvaluationBridgeKernel",
    "SQIChessCandidate",
    "SQIChessEvaluationBridgeResult",
    "run_full_chess_sqi_evaluation_bridge_kernel",
    "AionFullChessSQIGuidedMoveSelectionKernel",
    "SQIGuidedMoveSelectionResult",
    "run_full_chess_sqi_guided_move_selection_kernel",
    "AionFullChessLiveLoopSQISelectorAdapterKernel",
    "LiveLoopSQISelectorAdapterResult",
    "run_full_chess_live_loop_sqi_selector_adapter_kernel",
    "AionFullChessLiveLichessAutoplayV2SQILevel2Kernel",
    "LiveLichessAutoplayV2SQILevel2Result",
    "run_full_chess_live_lichess_autoplay_v2_sqi_level2_kernel",
    "AionFullChessRealLichessLevel2SQIAutoplayRunnerKernel",
    "RealLichessLevel2SQIAutoplayRunnerResult",
    "run_full_chess_real_lichess_level2_sqi_autoplay_runner_kernel",
    "AionFullChessRealLichessLevel2SQIGameLoopKernel",
    "RealLichessLevel2SQIGameLoopResult",
    "run_full_chess_real_lichess_level2_sqi_game_loop_kernel",
    "AionFullChessLevel2SQILossPostGameReviewKernel",
    "Level2SQILossPostGameReviewResult",
    "run_full_chess_level2_sqi_loss_post_game_review_kernel",
    "AionFullChessSQIFailurePatchSelectorKernel",
    "SQIFailurePatchSelectorResult",
    "run_full_chess_sqi_failure_patch_selector_kernel",
]

from .chess_like_threat_planner import (
    AionChessLikeThreatPlanner,
    ChessThreatLine,
    ChessActionEvaluation,
    ChessLikeThreatPlanningResult,
    run_chess_like_threat_planner,
)

from .mini_chess_legal_move_kernel import (
    AionMiniChessLegalMoveKernel,
    MiniChessPiece,
    MiniChessMove,
    MiniChessLegalMoveResult,
    run_mini_chess_legal_move_kernel,
)

from .mini_chess_threat_map_kernel import (
    AionMiniChessThreatMapKernel,
    MiniThreatPiece,
    MiniThreatMove,
    MiniChessThreatMapResult,
    run_mini_chess_threat_map_kernel,
)

from .mini_chess_capture_material_learning_kernel import (
    AionMiniChessCaptureMaterialLearningKernel,
    CaptureCandidate,
    MiniChessCaptureMaterialLearningResult,
    run_mini_chess_capture_material_learning_kernel,
)

from .mini_chess_self_play_learning_kernel import (
    AionMiniChessSelfPlayLearningKernel,
    MiniChessGameEpisode,
    MiniChessSelfPlayLearningResult,
    run_mini_chess_self_play_learning_kernel,
)

from .mini_chess_opponent_win_kernel import (
    AionMiniChessOpponentWinKernel,
    OpponentGameTurn,
    MiniChessOpponentWinResult,
    run_mini_chess_opponent_win_kernel,
)

from .mini_chess_full_loop_lock import (
    AionMiniChessFullLoopLock,
    MiniChessFullLoopResult,
    run_mini_chess_full_loop_lock,
)

from .full_chess_board_adapter_kernel import (
    AionFullChessBoardAdapterKernel,
    FullChessPiece,
    FullChessMove,
    FullChessBoardAdapterResult,
    run_full_chess_board_adapter_kernel,
)

from .full_chess_move_generator_kernel import (
    AionFullChessMoveGeneratorKernel,
    ChessPiece,
    ChessMove,
    FullChessMoveGeneratorResult,
    run_full_chess_move_generator_kernel,
)

from .full_chess_threat_map_kernel import (
    AionFullChessThreatMapKernel,
    ThreatPiece,
    ThreatMove,
    FullChessThreatMapResult,
    run_full_chess_threat_map_kernel,
)

from .full_chess_legal_move_safety_kernel import (
    AionFullChessLegalMoveSafetyKernel,
    SafetyPiece,
    SafetyMove,
    FullChessLegalMoveSafetyResult,
    run_full_chess_legal_move_safety_kernel,
)

from .full_chess_capture_evaluation_kernel import (
    AionFullChessCaptureEvaluationKernel,
    CapturePiece,
    CaptureCandidate,
    FullChessCaptureEvaluationResult,
    run_full_chess_capture_evaluation_kernel,
)

from .full_chess_opponent_reply_kernel import (
    AionFullChessOpponentReplyKernel,
    AionCandidateMove,
    FullChessOpponentReplyResult,
    run_full_chess_opponent_reply_kernel,
)

from .full_chess_one_ply_strategy_kernel import (
    AionFullChessOnePlyStrategyKernel,
    OnePlyCandidate,
    FullChessOnePlyStrategyResult,
    run_full_chess_one_ply_strategy_kernel,
)

from .full_chess_multi_ply_lookahead_kernel import (
    AionFullChessMultiPlyLookaheadKernel,
    LookaheadLine,
    FullChessMultiPlyLookaheadResult,
    run_full_chess_multi_ply_lookahead_kernel,
)

from .full_chess_game_loop_kernel import (
    AionFullChessGameLoopKernel,
    GameLoopTurn,
    FullChessGameLoopResult,
    run_full_chess_game_loop_kernel,
)

from .full_chess_learning_loop_kernel import (
    AionFullChessLearningLoopKernel,
    LearningSignal,
    FullChessLearningLoopResult,
    run_full_chess_learning_loop_kernel,
)

from .full_chess_self_play_improvement_kernel import (
    AionFullChessSelfPlayImprovementKernel,
    SelfPlayEpisode,
    FullChessSelfPlayImprovementResult,
    run_full_chess_self_play_improvement_kernel,
)

from .full_chess_self_play_tournament_kernel import (
    AionFullChessSelfPlayTournamentKernel,
    TournamentPolicy,
    TournamentMatch,
    FullChessSelfPlayTournamentResult,
    run_full_chess_self_play_tournament_kernel,
)

from .full_chess_tournament_learning_integration_kernel import (
    AionFullChessTournamentLearningIntegrationKernel,
    TournamentLearningUpdate,
    FullChessTournamentLearningIntegrationResult,
    run_full_chess_tournament_learning_integration_kernel,
)

from .full_chess_board_state_mutation_kernel import (
    AionFullChessBoardStateMutationKernel,
    BoardMutationMove,
    FullChessBoardStateMutationResult,
    run_full_chess_board_state_mutation_kernel,
)

from .full_legal_chess_rules_kernel import (
    AionFullLegalChessRulesKernel,
    LegalRuleCase,
    FullLegalChessRulesResult,
    run_full_legal_chess_rules_kernel,
)

from .full_chess_io_interface_kernel import (
    AionFullChessIoInterfaceKernel,
    UciMove,
    PgnRecord,
    FullChessIoInterfaceResult,
    run_full_chess_io_interface_kernel,
)

from .full_chess_real_opponent_game_loop_kernel import (
    AionFullChessRealOpponentGameLoopKernel,
    RealOpponentTurn,
    FullChessRealOpponentGameLoopResult,
    run_full_chess_real_opponent_game_loop_kernel,
)

from .full_chess_basic_search_engine_kernel import (
    AionFullChessBasicSearchEngineKernel,
    SearchCandidate,
    FullChessBasicSearchEngineResult,
    run_full_chess_basic_search_engine_kernel,
)

from .full_chess_self_play_training_kernel import (
    AionFullChessSelfPlayTrainingKernel,
    TrainingGame,
    FullChessSelfPlayTrainingResult,
    run_full_chess_self_play_training_kernel,
)

from .full_chess_rating_benchmark_kernel import (
    AionFullChessRatingBenchmarkKernel,
    BenchmarkMatch,
    FullChessRatingBenchmarkResult,
    run_full_chess_rating_benchmark_kernel,
)

from .full_chess_playable_ui_kernel import (
    AionFullChessPlayableUiKernel,
    UiMoveEntry,
    PlayableUiState,
    FullChessPlayableUiResult,
    run_full_chess_playable_ui_kernel,
)

from .full_chess_uci_engine_wrapper_kernel import (
    AionFullChessUciEngineWrapperKernel,
    UciCommandTrace,
    FullChessUciEngineWrapperResult,
    run_full_chess_uci_engine_wrapper_kernel,
)

from .full_chess_lichess_bot_bridge_kernel import (
    AionFullChessLichessBotBridgeKernel,
    LichessBridgeEvent,
    LichessMovePayload,
    FullChessLichessBotBridgeResult,
    run_full_chess_lichess_bot_bridge_kernel,
)

from .full_chess_live_lichess_bot_connector_kernel import (
    AionFullChessLiveLichessBotConnectorKernel,
    LichessConnectorConfig,
    LichessEndpointContract,
    FullChessLiveLichessBotConnectorResult,
    run_full_chess_live_lichess_bot_connector_kernel,
)

from .full_chess_guarded_live_move_execution_kernel import (
    AionFullChessGuardedLiveMoveExecutionKernel,
    GuardedLiveMoveRequest,
    GuardDecision,
    FullChessGuardedLiveMoveExecutionResult,
    run_full_chess_guarded_live_move_execution_kernel,
)

from .full_chess_autonomous_bot_learning_policy_kernel import (
    AionFullChessAutonomousBotLearningPolicyKernel,
    AutonomousLearningGame,
    FullChessAutonomousBotLearningPolicyResult,
    run_full_chess_autonomous_bot_learning_policy_kernel,
)

from .full_chess_real_game_result_learning_loop_kernel import (
    AionFullChessRealGameResultLearningLoopKernel,
    RealGameResult,
    RealGameLearningUpdate,
    FullChessRealGameResultLearningLoopResult,
    run_full_chess_real_game_result_learning_loop_kernel,
)

from .full_chess_knowledge_openings_strategy_book_kernel import (
    AionFullChessKnowledgeOpeningsStrategyBookKernel,
    ChessKnowledgeEntry,
    ChessKnowledgeQuery,
    FullChessKnowledgeOpeningsStrategyBookResult,
    run_full_chess_knowledge_openings_strategy_book_kernel,
)

from .full_chess_knowledge_guided_move_selection_kernel import (
    AionFullChessKnowledgeGuidedMoveSelectionKernel,
    CandidateMoveScore,
    FullChessKnowledgeGuidedMoveSelectionResult,
    run_full_chess_knowledge_guided_move_selection_kernel,
)

from .full_chess_local_engine_match_harness_kernel import (
    AionFullChessLocalEngineMatchHarnessKernel,
    LocalOpponentProfile,
    LocalMatchRecord,
    FullChessLocalEngineMatchHarnessResult,
    run_full_chess_local_engine_match_harness_kernel,
)

from .full_chess_local_tournament_rating_ladder_kernel import (
    AionFullChessLocalTournamentRatingLadderKernel,
    LadderTierResult,
    FullChessLocalTournamentRatingLadderResult,
    run_full_chess_local_tournament_rating_ladder_kernel,
)

from .full_chess_lichess_dry_run_game_replay_kernel import (
    AionFullChessLichessDryRunGameReplayKernel,
    LichessReplayEvent,
    DryRunReplayDecision,
    FullChessLichessDryRunGameReplayResult,
    run_full_chess_lichess_dry_run_game_replay_kernel,
)

from .full_chess_live_lichess_bot_enablement_kernel import (
    AionFullChessLiveLichessBotEnablementKernel,
    LiveLichessBotEnablementConfig,
    LiveLichessBotEnablementDecision,
    FullChessLiveLichessBotEnablementResult,
    run_full_chess_live_lichess_bot_enablement_kernel,
)

from .full_chess_real_lichess_network_move_sender_kernel import (
    AionFullChessRealLichessNetworkMoveSenderKernel,
    RealLichessMoveSendRequest,
    RealLichessMoveSendResult,
    run_full_chess_real_lichess_network_move_sender_kernel,
)

from .full_chess_live_lichess_game_loop_result_recorder_kernel import (
    AionFullChessLiveLichessGameLoopResultRecorderKernel,
    LiveLichessGameLoopMoveRecord,
    FullChessLiveLichessGameLoopResult,
    run_full_chess_live_lichess_game_loop_result_recorder_kernel,
)

from .full_chess_post_game_blunder_review_kernel import (
    AionFullChessPostGameBlunderReviewKernel,
    PostGameMoveReview,
    FullChessPostGameBlunderReviewResult,
    run_full_chess_post_game_blunder_review_kernel,
)

from .full_chess_real_evaluation_function_kernel import (
    AionFullChessRealEvaluationFunctionKernel,
    RealChessEvaluationBreakdown,
    RealChessEvaluationResult,
    run_full_chess_real_evaluation_function_kernel,
)

from .full_chess_evaluation_guided_move_selection_kernel import (
    AionFullChessEvaluationGuidedMoveSelectionKernel,
    EvaluationGuidedCandidateMove,
    EvaluationGuidedMoveSelectionResult,
    run_full_chess_evaluation_guided_move_selection_kernel,
)

from .full_chess_depth_limited_lookahead_search_kernel import (
    AionFullChessDepthLimitedLookaheadSearchKernel,
    DepthLimitedSearchCandidate,
    DepthLimitedLookaheadSearchResult,
    run_full_chess_depth_limited_lookahead_search_kernel,
)

from .full_chess_live_loop_search_selector_adapter_kernel import (
    AionFullChessLiveLoopSearchSelectorAdapterKernel,
    LiveLoopSearchSelectorAdapterResult,
    run_full_chess_live_loop_search_selector_adapter_kernel,
)

from .full_chess_live_lichess_autoplay_v2_level2_kernel import (
    AionFullChessLiveLichessAutoplayV2Level2Kernel,
    LiveLichessAutoplayV2Level2Result,
    run_full_chess_live_lichess_autoplay_v2_level2_kernel,
)

from .full_chess_sqi_evaluation_bridge_kernel import (
    AionFullChessSQIEvaluationBridgeKernel,
    SQIChessCandidate,
    SQIChessEvaluationBridgeResult,
    run_full_chess_sqi_evaluation_bridge_kernel,
)

from .full_chess_sqi_guided_move_selection_kernel import (
    AionFullChessSQIGuidedMoveSelectionKernel,
    SQIGuidedMoveSelectionResult,
    run_full_chess_sqi_guided_move_selection_kernel,
)

from .full_chess_live_loop_sqi_selector_adapter_kernel import (
    AionFullChessLiveLoopSQISelectorAdapterKernel,
    LiveLoopSQISelectorAdapterResult,
    run_full_chess_live_loop_sqi_selector_adapter_kernel,
)

from .full_chess_live_lichess_autoplay_v2_sqi_level2_kernel import (
    AionFullChessLiveLichessAutoplayV2SQILevel2Kernel,
    LiveLichessAutoplayV2SQILevel2Result,
    run_full_chess_live_lichess_autoplay_v2_sqi_level2_kernel,
)

from .full_chess_real_lichess_level2_sqi_autoplay_runner_kernel import (
    AionFullChessRealLichessLevel2SQIAutoplayRunnerKernel,
    RealLichessLevel2SQIAutoplayRunnerResult,
    run_full_chess_real_lichess_level2_sqi_autoplay_runner_kernel,
)

from .full_chess_real_lichess_level2_sqi_game_loop_kernel import (
    AionFullChessRealLichessLevel2SQIGameLoopKernel,
    RealLichessLevel2SQIGameLoopResult,
    run_full_chess_real_lichess_level2_sqi_game_loop_kernel,
)

from .full_chess_level2_sqi_loss_post_game_review_kernel import (
    AionFullChessLevel2SQILossPostGameReviewKernel,
    Level2SQILossPostGameReviewResult,
    run_full_chess_level2_sqi_loss_post_game_review_kernel,
)

from .full_chess_sqi_failure_patch_selector_kernel import (
    AionFullChessSQIFailurePatchSelectorKernel,
    SQIFailurePatchSelectorResult,
    run_full_chess_sqi_failure_patch_selector_kernel,
)

from .full_chess_positional_strategy_features_kernel import run_full_chess_positional_strategy_features_kernel

from .full_chess_goal_biased_strategic_search_kernel import run_full_chess_goal_biased_strategic_search_kernel

from .full_chess_simple_plan_following_kernel import run_full_chess_simple_plan_following_kernel

from .full_chess_post_game_strategic_review_policy_kernel import run_full_chess_post_game_strategic_review_policy_kernel

from .full_chess_self_play_curriculum_kernel import run_full_chess_self_play_curriculum_kernel

from .full_chess_long_term_plan_generation_kernel import run_full_chess_long_term_plan_generation_kernel

from .full_chess_consequence_simulation_risk_forecasting_kernel import run_full_chess_consequence_simulation_risk_forecasting_kernel

from .full_chess_strategic_concept_memory_kernel import run_full_chess_strategic_concept_memory_kernel

from .full_chess_concept_guided_search_plan_bias_kernel import run_full_chess_concept_guided_search_plan_bias_kernel

from .full_chess_concept_guided_move_reranking_kernel import run_full_chess_concept_guided_move_reranking_kernel

from .full_chess_local_concept_guided_game_loop_kernel import run_full_chess_local_concept_guided_game_loop_kernel

from .full_chess_concept_guided_live_lichess_dry_run_adapter_kernel import run_full_chess_concept_guided_live_lichess_dry_run_adapter_kernel

from .full_chess_guarded_concept_guided_live_sender_gate_kernel import run_full_chess_guarded_concept_guided_live_sender_gate_kernel

from .full_chess_live_level2_preflight_checklist_kernel import run_full_chess_live_level2_preflight_checklist_kernel

from .full_chess_one_move_live_smoke_test_gate_kernel import run_full_chess_one_move_live_smoke_test_gate_kernel

from .full_chess_live_level2_one_move_authorized_sender_kernel import run_full_chess_live_level2_one_move_authorized_sender_kernel

from .full_chess_level2_live_post_game_evidence_review_kernel import run_full_chess_level2_live_post_game_evidence_review_kernel

from .full_chess_queen_endgame_mate_conversion_kernel import run_full_chess_queen_endgame_mate_conversion_kernel

from .full_chess_queen_endgame_override_live_sender_kernel import run_full_chess_queen_endgame_override_live_sender_kernel

from .full_chess_live_post_400_recovery_kernel import run_full_chess_live_post_400_recovery_kernel

from .full_chess_level2_live_rematch_recovery_loop_kernel import run_full_chess_level2_live_rematch_recovery_loop_kernel

from .full_chess_level2_live_rematch_runner_with_recovery_kernel import run_full_chess_level2_live_rematch_runner_with_recovery_kernel

from .full_chess_zugzwang_choice_architecture_selector_kernel import run_full_chess_zugzwang_choice_architecture_selector_kernel

from .full_chess_one_ply_blunder_guard_kernel import run_full_chess_one_ply_blunder_guard_kernel

from .full_chess_opponent_threat_map_kernel import run_full_chess_opponent_threat_map_kernel

from .full_chess_passed_pawn_conversion_policy_kernel import run_full_chess_passed_pawn_conversion_policy_kernel

from .full_chess_endgame_box_mate_net_builder_kernel import run_full_chess_endgame_box_mate_net_builder_kernel

from .full_chess_plan_continuity_memory_kernel import run_full_chess_plan_continuity_memory_kernel

from .full_chess_rook_bishop_repetition_breaker_kernel import run_full_chess_rook_bishop_repetition_breaker_kernel

from .full_chess_strategic_regression_well_optimiser_kernel import run_full_chess_strategic_regression_well_optimiser_kernel

from .full_chess_level2_strategic_well_live_sender_integration_kernel import run_full_chess_level2_strategic_well_live_sender_integration_kernel

from .full_chess_proactive_plan_primacy_intent_driver_kernel import run_full_chess_proactive_plan_primacy_intent_driver_kernel

from .full_chess_intent_driven_strategic_regression_well_kernel import run_full_chess_intent_driven_strategic_regression_well_kernel

from .full_chess_live_one_move_strategic_well_sender_kernel import run_full_chess_live_one_move_strategic_well_sender_kernel

from .full_chess_level2_strategic_well_live_rematch_kernel import run_full_chess_level2_strategic_well_live_rematch_kernel

from .full_chess_level2_strategic_well_live_post_game_review_kernel import run_full_chess_level2_strategic_well_live_post_game_review_kernel

from .full_chess_promotion_choice_queen_first_guard_kernel import run_full_chess_promotion_choice_queen_first_guard_kernel

from .full_chess_passed_pawn_intent_scope_guard_kernel import run_full_chess_passed_pawn_intent_scope_guard_kernel

from .full_chess_anti_shuffling_endgame_conversion_guard_kernel import run_full_chess_anti_shuffling_endgame_conversion_guard_kernel

from .full_chess_proactive_intent_primacy_plan_enforcement_kernel import run_full_chess_proactive_intent_primacy_plan_enforcement_kernel

from .full_chess_dynamic_intent_switching_plan_strength_kernel import run_full_chess_dynamic_intent_switching_plan_strength_kernel

from .full_chess_promotion_safety_queen_survival_guard_kernel import run_full_chess_promotion_safety_queen_survival_guard_kernel

from .full_chess_initiative_hygiene_guard_kernel import run_full_chess_initiative_hygiene_guard_kernel

from .full_chess_king_safety_threat_removal_policy_kernel import run_full_chess_king_safety_threat_removal_policy_kernel

from .full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel import run_full_chess_critical_threat_hygiene_queen_intrusion_trap_policy_kernel
from .full_chess_opponent_reply_probability_tactical_exposure_guard_kernel import run_full_chess_opponent_reply_probability_tactical_exposure_guard_kernel
from .full_chess_monte_carlo_policy_value_seed_kernel import run_full_chess_monte_carlo_policy_value_seed_kernel
from backend.modules.aion_games.full_chess_rolling_strategic_plan_kernel import run_full_chess_rolling_strategic_plan_kernel
from backend.modules.aion_games.full_chess_opponent_response_beam_planner_kernel import run_full_chess_opponent_response_beam_planner_kernel
from backend.modules.aion_games.full_chess_parallel_opponent_beam_router_sqi_collapse_kernel import run_full_chess_parallel_opponent_beam_router_sqi_collapse_kernel
