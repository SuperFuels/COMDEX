# Model execution preservation and storage cleanup

This record preserves the distinction between executable model artifacts,
rebuild recipes, and experimental evidence. Cleanup was authorized on
13 September 2026 to recover internal disk reserve for the 120B programme.
`cleanup_inventory.json` records the exact selected paths. Its status records
whether cleanup has actually happened.

## Retained artifacts

- `/Applications/Tessaris.app`: current installed application. None of the
  selected backup copies has a newer `app.asar` timestamp.
- The complete verified GPT-OSS 120B SD warehouse and its manifests.
- The promoted 20 GiB internal-disk 120B L2 cartridge.
- Every verified and interrupted current teacher capture and correction report.
- One complete original Granite BF16 expert layer-pack set:
  `/Users/kevinrobinson/AION-Artifact-Archive/2026-09-09-granite-layer-packs/granite-3.1-3b-a800m-v1`.
  All 32 layer files were checked against the stored SHA-256 values before
  selecting other derived packs for deletion. This retains all 1,280 experts.
- Metadata, manifests, invalidation records and the relocation record from
  every archived Granite pack variant, copied into `granite-metadata/`.
- Local source code, native kernels, build scripts, tests and technical records.
  A remote source snapshot includes the outstanding desktop, frontend,
  inference and Unity source changes without changing the local working tree.

## Selected removable artifacts

The 145 named old Tessaris application copies are packaged builds, not the
source repository. Ollama model files are unused by the present native 120B
programme; the Ollama application configuration and keys are not selected.

The seven archived Qwen screening/edge GGUF files are experimental derived
variants, not the successful Q2 expert candidate identified in
`QWEN30B_Q2_EXPERT_RESIDENT_RESULT_2026-09-09.tex`. Five redundant Granite pack
variants can be discarded while retaining one complete original expert set.
All pack manifests and failure records are preserved even when weights are
removed. The original manifests are historical evidence and retain their
original paths; they must not be silently edited or described as directly
usable after relocation.

## What consumers need

A working distribution needs model weights, tokenizer/configuration and shared
backbone tensors, the appropriate AION expert representation and manifests,
runtime/native kernels, compatible dependencies, and a documented launch and
integrity-check procedure. The Git repository supplies implementation and
recipes; it does not itself contain every multi-gigabyte model artifact.

The formerly mounted small-model SD root is not mounted now. The promoted
Granite INT8 bank and complete small-model checkpoints have therefore not been
confirmed available in this cleanup audit. Retaining the original BF16 expert
packs protects their numerical content, but those packs alone are not a full
language model: shared backbone tensors, configuration and tokenizer are also
required. Do not claim that a consumer-ready bundle or a fresh small-model
reproduction was validated during this cleanup.

## Granite rebuild chain

The existing, versioned implementation chain is:

1. Obtain/restore the original checkpoint plus tokenizer/configuration and
   verify its identity using the original experiment evidence.
2. `backend/scripts/build_aion_moe_expert_shards.py` accepts `--model-path`,
   `--storage-root`, and optional `--output-root`, and produces verified expert
   shards. The retained layer packs also contain each expert's original
   `experts.<id>.input_linear.weight` and
   `experts.<id>.output_linear.weight` tensors if checkpoint recovery is needed.
3. `backend/scripts/build_aion_int8_glyph_blocks.py` accepts `--storage-root`,
   `--source-manifest`, and `--destination`, and builds symmetric per-output-row
   INT8 blocks with FP16 scales and hash-bound indices.
4. `backend/scripts/build_aion_int8_dynamic_banks.py` accepts `--storage-root`,
   `--glyph-manifest`, and `--destination`, and builds the contiguous 40-expert
   banks for all 32 layers.
5. `backend/scripts/run_aion_int8_sparse_dispatch_full_model.py` accepts
   `--storage-root`, `--model-path`, `--source-manifest`, `--glyph-manifest`,
   `--dynamic-bank-manifest`, `--dynamic-bank-gate`, and `--output` for the
   recorded dynamic-bank comparison. Semantic and teacher-probability checks
   are in `run_aion_dynamic_bank_semantic_gate.py` and
   `run_aion_dynamic_bank_teacher_quality.py`.

Use the complete CLI help and the main AION README when assembling a fresh
environment. Do not simply reuse absolute-path manifests on another computer;
rebuild valid bindings and run the integrity and quality gates. Retain model
licence/provenance information when distributing weights.

## Qwen and GPT-OSS recipes and claims

The Qwen record preserves the control identity, llama.cpp build 10809
(`5266f24da`), and the transformation: only `ffn_gate_exps.weight`,
`ffn_up_exps.weight` and `ffn_down_exps.weight` were requantized to Q2_K;
non-expert tensors retained the Q4_K_M selection. The successful candidate
identity and measured quality boundaries remain in the technical record.
Removing screening variants does not remove that implementation record.
A newly rebuilt model must be verified and retested, rather than automatically
inheriting the previous benchmark claim.

The active 120B execution instructions remain in `SD_ONLY_EXECUTION_PLAN.md`
and `GPT_OSS_120B_DETAILED_HANDOVER_2026-09-12.tex`. Its complete selected
representation and working native runtime are retained. This cleanup does not
change model arithmetic, weaken accuracy gates, certify a correction, or
establish a new generation speed.
