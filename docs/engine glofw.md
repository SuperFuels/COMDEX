graph TD

subgraph Orchestrator
  TO[tick_orchestrator.py]
  TM[tick_module.py]
end

subgraph Engines
  EA[Engine A]
  EB[Engine B]
  ES[hyperdrive_engine_sync.py]
end

subgraph Milestones
  MT[milestone_tracker.py]
  WC[warp_checks.py]
  ID[idle_manager_module.py]
end

subgraph Tuning
  ST[safe_tuning_module.py]
  HC[harmonic_coherence_module.py]
  DM[drift_damping.py]
  HA[hyperdrive_auto_tuner_module.py]
  HT[hyperdrive_tuning_constants_module.py]
end

subgraph Feedback & SQI
  SQ[sqi_feedback_module.py]
  SR[sqi_reasoning_module.py]
  SC[sqi_controller_module.py]
  SM[sqi_module.py]
end

subgraph Runtime + Exhaust
  EX[exhaust_module.py]
  VE[virtual_exhaust_module.py]
  GS[gear_shift_module.py]
  EM[engine_factory_module.py]
  ER[ecu_runtime_module.py]
  EO[ecu_runtime_orchestrator_module.py]
end

subgraph Injectors & State
  TI[tesseract_injector.py]
  PM[pulse_module.py]
  SM2[state_manager_module.py]
  BS[best_state_module.py]
end

subgraph Interface
  HTM[hyperdrive_terminal.py]
  HFB[hyperdrive_field_bridge.py]
  CLI[cli_parser_module.py]
  IO[dc_io.py]
end

TO --> TM
TM --> EA
TM --> EB
TM --> MT
TM --> WC
TM --> SQ
TM --> EX
TM --> VE
TM --> SR
TM --> SC
TM --> GS
TM --> TI
TM --> HT
TM --> HC
TM --> DM
TM --> ST
TM --> HA
TM --> HTM
TM --> HFB
TM --> CLI

EA --> EX
EA --> VE
EA --> SQ
EA --> GS
EB --> EX
EB --> VE
EB --> SQ
EB --> GS

MT --> ID
WC --> ID

SQ --> SC
SQ --> SR
SC --> SM
SR --> HC
SR --> ST

TI --> PM
SM2 --> BS
ER --> EO`