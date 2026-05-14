CodexCore / sTPU ISA Manual (v0.2)

0. Scope & Goals
	•	Target: Phase-1 (compat layer on classical HW), Phase-2 (hybrid JIT), Phase-3 (native sTPU).
	•	Purpose: Replace binary ISA semantics with symbolic glyph instructions that compress logic, preserve meaning (lineage, SQI, entropy), and enable entangled parallelism.
	•	Audience: Engine/runtime implementers, compiler (CodexLang) authors, hardware (sTPU) architects.

⸻

1) Machine Model

1.1 Register File
	•	General glyph registers (GR): GR0..GR31 (scalars, tensors, glyph objects)
	•	Special registers
	•	GRZ (read-only zero)
	•	GRF (flags register; symbolic flags bitfield)
	•	GRE (entropy accumulator)
	•	GRS (SQI accumulator / milestone counter)
	•	GRC (control/status; scheduler hints, privilege mask)
	•	GRP (program counter in bytecode stream)
	•	GRT (temporary working reg for syscalls / traps)

Phase-1 mapping: GRs bind to host memory slots; Phase-3 maps to physical sTPU banks.

1.2 Memory Spaces
	•	GMEM (Glyph Memory): objects, glyph trees, tags, proofs, lineage.
	•	TMEM (Tensor Memory): dense tensors/matrices/vectors.
	•	SMEM (Stream/Message): queues for I/O, IPC, network beams.
	•	CMEM (Container Memory): .dc container-local state & indexes.
	•	IMEM (Instruction Memory): symbolic bytecode stream.

Addressing modes
	•	Direct: @addr
	•	Indirect: [GRi], [GRi + imm]
	•	Slice/View: [GRi]{shape,strides} (tensors)
	•	Broadcast: [GRi]^b (expand rank)

1.3 Flags (GRF layout)

Bit                                                 Name                                    Meaning (sticky unless cleared)
0                                                   ⊙ (collapse)                            Superposition → concrete state occurred
1                                                   ↔ (entangled)                           New entanglement edge(s) formed
2                                                   ∇ (entropy)                             Entropy increased above threshold
3
⟲ (mutated)
Operand/result was mutated (new version)
4
✦ (milestone)
SQI milestone crossed (SRP update)
5
⚖ (soullaw)
Rule gate checked/raised
6
E (exception)
Trap/exception latched
7
Y (yield)
Scheduler hint to yield/park beam


GRE accumulates continuous entropy; GRS accumulates SQI.

1.4 Execution Pipeline
	1.	Fetch bytecode word
	2.	Decode glyph + operand spec
	3.	Schedule beams (entanglement-aware)
	4.	Execute (scalar/tensor/glyph engines)
	5.	Collapse (if needed)
	6.	Commit results + update flags & counters
	7.	Trace (HUD/KG hooks if enabled)

Determinism: GRC.deterministic = 1 enforces repeatable beam scheduling (testing/replay).

⸻

2) Bytecode Encoding (Variable Length Word)


+----------+---------+----------------+----------------+-----------------+
| OPCODE   | FLAGS   | OPERAND COUNT  | OPERAND REFS   | MODIFIERS (TLV) |
+----------+---------+----------------+----------------+-----------------+
  8 bits     8 bits        4 bits         n × 16 bits        variable

  	•	OPCODE (8b): glyph ID (see opcode map).
	•	FLAGS (8b): request/affect mask (which symbolic flags to evaluate/update).
	•	OPERAND COUNT (4b): 0–15 operands.
	•	OPERAND REFS (n×16b): each ref encodes class(2b) + index(14b)
	•	Class: 00=GR, 01=mem handle, 10=immediate slot, 11=reserved
	•	MODIFIERS (TLV): sequence of (type:8b, len:8b, value:len bytes)
	•	Common TLVs: IMM_SCALAR, IMM_SHAPE, TAG_ENTANGLE_ID, SQI_MASK, PRIV_MASK, SCHED_HINT, IO_CHAN, SLICE, BROADCAST

Endianness: little-endian for multi-byte TLVs.
Versioning: stream starts with MAGIC("SBC1") + ABI_VERSION.

⸻

3) Opcode Map (summary)

Atomic (0x01–0x1F)
⊕(01), ⊖(02), ⊗(03), ÷(04), ↔(05), ≠(06), ≥(07), ≤(08), ∇(09), ⟲(0A), →(0B), ⊙(0C), ⊼(0D ANDN), ⊻(0E XOR), ¬(0F NOT), ⌈⌉(10 CEIL), ⌊⌋(11 FLOOR), |·|(12 ABS), sgn(13 SIGN), √(14 SQRT)

Composite (0x20–0x3F)
∑(20), ∫(21), ⧖(22 SYNC), ⟡(23 CONV), ⨀(24 DOT), ⊞(25 MADD), ⊠(26 MMUL), 𝕊(27 STEP), ⧫(28 REDUCE), ⟡⟲(29 CONV_MUT), ↻(2A LOOP), ⫴(2B CONCAT), ⫽(2C SPLIT), ⤧(2D TRANSPOSE)

Meta / Syscalls (0x40–0x5F)
⟦ALLOC⟧(40), ⟦FREE⟧(41), ⟦IO⟧(42), ⟦FORK⟧(43), ⟦JOIN⟧(44), ⟦SCHED⟧(45), ⟦RULE⟧(46), ⟦KG⟧(47), ⟦HUD⟧(48), ⟦NET⟧(49), ⟦CALL⟧(4A), ⟦RET⟧(4B), ⟦MAP⟧(4C JIT map), ⟦PIN⟧(4D pin mem), ⟦UNPIN⟧(4E)

Below, every glyph page follows the same “datasheet” structure.

⸻

4) Instruction Datasheets — ATOMIC

4.1 ⊕ — ADD (Opcode 0x01)
	•	Form: ⊕ dst, srcA, srcB (+ optional IMM_SCALAR to add immediate)
	•	Inputs: srcA, srcB (scalar/tensor/glyph-numeric)
	•	Outputs: dst (type union of inputs; broadcast if ranks differ)
	•	Flags: sets ∇ (if variance ↑), may set ↔ (if entangle TLV given), ✦ (if SQI crosses)
	•	Pseudocode:


dst.value = add(srcA, srcB)           // elementwise for tensors
if TLV.TAG_ENTANGLE_ID: mark_entangled(dst, srcA, srcB, tag)
GRE += entropy_change(dst)
if gre_delta > θ_ent: set(GRF.∇)
if sqi(dst) crosses milestone: set(GRF.✦); GRS += Δ

	•	Trace (example):

[QPU] ⊕ GR2, GR0, GR1
[Trace] GR2 = GR0 + GR1
[Flags] ∇=1 (Δ=0.03), ↔=0, ✦=0

	•	Exceptions: type mismatch (E), shape mismatch w/o broadcast (E), NaG propagate.
	•	Notes: Accepts SLICE/BROADCAST TLVs to control tensor alignment.

⸻

4.2 ⊖ — SUB (0x02)
	•	Same mechanics as ⊕ with subtraction.
	•	Flags: ∇ (if variance change), ⟲ not set here.
	•	Pseudocode: dst = sub(srcA, srcB)

⸻

4.3 ⊗ — MUL (0x03)
	•	Form: ⊗ dst, srcA, srcB
	•	Flags: ↔ often set when TAG_ENTANGLE_ID present (used in fused kernels), ✦ on milestone.
	•	Pseudocode: dst = mul(srcA, srcB) (elementwise; MMUL is composite 0x26)

⸻

4.4 ÷ — DIV (0x04)
	•	Form: ÷ dst, srcA, srcB
	•	Exceptions: divide-by-zero → set E, produce NaG unless MODIFIERS{ON_ZERO:policy} present.

⸻

4.5 ↔ — EQUIVALENCE (0x05)
	•	Form: ↔ dst, A, B
	•	Outputs: boolean scalar/tensor or entanglement handle; controlled by TLV MODE:{BOOL|ENT}
	•	Flags: ↔, optionally ⊙ (if collapse required for comparison), ∇ if uncertainty changes
	•	Pseudocode:

if MODE==BOOL: dst = equal(A,B)
else: eid = entangle(A,B,TLV.TAG_ENTANGLE_ID); dst = eid
set(GRF.↔)

	•	Trace:

[Beam eq/entangle] stage=entangle eid=eid::7fa.. payload={...}

	•	Notes: Central to beam lineages and sTPU scheduling.

⸻

4.6 ≠ — INEQUALITY (0x06)
	•	Like ↔(BOOL) inverted; flags ∇ on uncertainty changes.

⸻

4.7 ≥ / ≤ — COMPARE (0x07 / 0x08)
	•	Form: ≥ dst, A, B (bool mask); ∇ if comparison raises ambiguity in superposed states (collapse if required).

⸻

4.8 ∇ — GRADIENT (0x09)
	•	Form: ∇ dst, A[, dir]
	•	Inputs: A (scalar/tensor); optional dir or TLV MODE:{AUTO|DIR|NUM}
	•	Outputs: gradient tensor aligned with A
	•	Flags: ∇ (always), ✦ if gradient norm crosses threshold
	•	Pseudocode:

dst = gradient(A, dir or autodiff)
GRE += norm(dst) * γ
set(GRF.∇)

	•	Notes: Phase-1 can call out to SymPy/Autograd.

⸻

4.9 ⟲ — MUTATE (0x0A)
	•	Form: ⟲ dst, src[, seed]
	•	Semantics: produces a new version of src specified by mutation policy (TLV: MUT_POLICY)
	•	Flags: ⟲ set; ∇ may update; entanglement preserved if PRESERVE_ENT
	•	Pseudocode:

dst = mutate(src, seed, policy)
set(GRF.⟲)

	•	Notes: Used in evolutionary kernels (Codex DNA writer).

⸻

4.10 → — TRIGGER / BRANCH (0x0B)
	•	Form: → target_label, cond
	•	Flags: ✦ (milestone), Y (scheduler yield) possible
	•	Pseudocode:

if truthy(cond): GRT = PC; PC = label_addr
else: continue

	•	Notes: High-level inversion of CMP/JMP; works on boolean tensors (branch if any/all per TLV).

⸻

4.11 ⊙ — COLLAPSE (0x0C)
	•	Form: ⊙ dst, superposed
	•	Effect: force collapse of superposition; record collapse trace
	•	Flags: ⊙=1, ∇ may drop
	•	Pseudocode:

dst = collapse(superposed, policy=TLV.COLLAPSE_MODE)
set(GRF.⊙)

4.12 ⊻ — XOR (0x0E)
	•	Tensor/bitwise symbolic XOR; used in hashing, beam IDs.

⸻

4.13 ¬ — NOT (0x0F), |·| ABS (0x12), √ SQRT (0x14)
	•	Standard elementwise semantics with symbolic flags (entropy/milestone thresholds optional).

⸻

5) Instruction Datasheets — COMPOSITE

5.1 ∑ — SUMMATION (0x20)
	•	Form: ∑ dst, src[, axis|mask]
	•	Inputs: tensor src; TLVs: AXIS, MASK, KEEP_DIMS
	•	Outputs: reduced tensor/scalar
	•	Flags: ∇ on variance change; ✦ if reduction meets criterion
	•	Pseudocode:

dst = reduce_sum(src, axis=TLV.AXIS, mask=TLV.MASK)
if sqi(dst) > θ: set(✦)



	•	Trace:

    [QPU] ∑ GR3, GR2 axis=1
[Sheet] reduce: time=0.8ms, beams=4

5.2 ∫ — INTEGRAL (0x21)
	•	Form: ∫ dst, f, range[, step]
	•	Semantics: numerical integration (composite of ∑ + ⊗) with prediction forks
	•	Flags: ∇, ✦ (if integral hits target), ↔ (if entangled param)
	•	Pseudocode:

dst = integrate(f, range, method=TLV.METHOD)
fork_predictions(dst) if TLV.PREDICT=1

5.3 ⧖ — SYNC (0x22)
	•	Form: ⧖ [eid or ALL]
	•	Semantics: barrier for entangled beams; collapse or join as policy dictates
	•	Flags: may set ⊙
	•	Notes: Used to control Phase-8 lineage entanglement.

5.4 ⟡ — CONVOLUTION (0x23)
	•	Form: ⟡ out, x, w[, stride, pad, dilation]
	•	Inputs: tensor x, kernel w
	•	Outputs: tensor out
	•	Flags: ↔ (entangle x↔w), ✦ (if activation milestone)
	•	Notes: sTPU can fuse ⟡ + activation + ⊞ into a single kernel (Phase-3).

5.5 ⨀ — DOT (0x24)
	•	Form: ⨀ out, a, b (vector dot / batched)
	•	Flags: may set ↔; uses tensor cores on sTPU.

5.6 ⊞ — MATRIX ADD (0x25)
	•	Batched ⊕ with broadcasting controls.

5.7 ⊠ — MATRIX MUL (0x26)
	•	Form: ⊠ out, A, B
	•	Notes: maps to GEMM; Phase-1 JIT to BLAS, Phase-3 native matmul tiles.

5.8 𝕊 — SYMBOLIC STEP (0x27)
	•	Form: 𝕊 step_out, state_in, fn[, steps]
	•	Semantics: iterator micro-kernel with SQI checkpointing
	•	Flags: ✦ when checkpoint triggers; may set Y to yield.

5.9 ⧫ — REDUCE (0x28)
	•	Generic reduction; TLV OP:{SUM,MAX,MIN,MEAN,LOGSUMEXP,...}

5.10 ⟡⟲ — CONV_MUTATE (0x29)
	•	Fused conv + mutate (e.g., neuroevolution, style transfer); flags ⟲, ↔, ✦.

5.11 ↻ — LOOP (0x2A)
	•	Form: ↻ label, count|cond
	•	Semantics: loop construct with optional entangled counter; break on rule/trap.

5.12 ⫴ / ⫽ / ⤧ (Concat/Split/Transpose)
	•	Tensor layout ops; ensure slice/swap trace is recorded (for reversible replay).

⸻

6) Instruction Datasheets — META / SYSCALLS

6.1 ⟦ALLOC⟧ (0x40)
	•	Form: ⟦ALLOC⟧ dst_handle, shape[, dtype, space={GMEM|TMEM|SMEM}]
	•	Effect: allocate memory region; returns handle in dst_handle
	•	Flags: none by default; E on failure
	•	Pseudocode:

dst = mem_alloc(shape,dtype,space)
if !dst: set(E)

6.2 ⟦FREE⟧ (0x41)
	•	Free handle; set E if invalid or still entangled (unless FORCE).

6.3 ⟦IO⟧ (0x42)
	•	Form: ⟦IO⟧ op, arg0, arg1... with TLVs IO_CHAN, MODE
	•	Examples: print/log, file read/write, device read (Phase-1 → host bridge)

6.4 ⟦FORK⟧ (0x43) / ⟦JOIN⟧ (0x44)
	•	Beam/process management; returns beam_id; JOIN collapses results per policy.

6.5 ⟦SCHED⟧ (0x45)
	•	Yield, set priority, pin to device group, park/resume.

6.6 ⟦RULE⟧ (0x46)
	•	SoulLaw gate: evaluate rule; ⚖ flag set; may raise trap/block.

6.7 ⟦KG⟧ (0x47)
	•	Inject/read knowledge graph entries; ties into KnowledgeGraphWriter.

6.8 ⟦HUD⟧ (0x48)
	•	Emit HUD/GHX events; Phase-1 just logs; Phase-3 streams overlay metadata.

6.9 ⟦NET⟧ (0x49)
	•	Open symbolic channels, entangle remote peers; supports E2E_TAG, ENC_POLICY.

6.10 ⟦CALL⟧ (0x4A) / ⟦RET⟧ (0x4B)
	•	ABI:
	•	Args in GR0..GR7, ret in GR0
	•	Caller-saved: GR0..GR15, Callee-saved: GR16..GR31
	•	GRT used for return address if needed; or call stack in GMEM

6.11 ⟦MAP⟧ (0x4C)
	•	JIT mapping: bind glyph to host intrinsic (BLAS, cuDNN) with capability mask.

6.12 ⟦PIN⟧ / ⟦UNPIN⟧ (0x4D/0x4E)
	•	Lock memory pages for DMA / device residency (sTPU & NIC zero-copy).

⸻

7) Calling Convention & ABI
	•	Function entry: callee can read GRC.priv, GRC.cap_mask.
	•	Stack model: optional symbolic stack in GMEM; small frames in registers.
	•	Varargs: pass pointer to tuple in GMEM via GR1.
	•	Exceptions: trap sets GRF.E=1, pushes fault record to SMEM (unless masked).
	•	Syscall gates: privileged ops require GRC.priv ≥ 1.

⸻

8) Concurrency & Memory Model
	•	Entangled Consistency: Writes to entangled sets appear atomically at ⧖.
	•	Release/Acquire: TLV MEM_ORDER:{REL, ACQ, REL_ACQ, SC} per instruction.
	•	Deadlock handling: ⧖ has timeout TLV; raise trap on exceed.
	•	Determinism: GRC.deterministic enforces stable beam scheduling for tests.

⸻

9) Security & SoulLaw
	•	All Meta ops can be guarded by ⟦RULE⟧ prechecks (compile-time or runtime).
	•	Privilege Levels: 0=user, 1=service, 2=system, 3=hypervisor.
	•	Audit: HUD/KG logs include cause→effect reverse trace IDs.

⸻

10) Performance Counters (per glyph & per beam)
	•	cycles, bytes_read/written, entropy_delta, sqi_delta, collapse_count, entangle_edges, jit_hits/misses.
	•	Export via ⟦HUD⟧ or mapped memory region.

⸻

11) Example: End-to-End Program

11.1 CodexLang

W = ⟡(X, K, stride=2)
y = ⨀(W, v)
if (y ≥ θ):
  ⟦IO⟧("print", y)
else:
  y = ⟲(y, seed=42)  // mutate
return y

11.2 sTPU Assembly

⟦ALLOC⟧ GR10, shape=[B,C,H,W], dtype=f16, space=TMEM   ; X
⟦ALLOC⟧ GR11, shape=[C,kh,kw], dtype=f16, space=TMEM   ; K
⟦ALLOC⟧ GR12, shape=[B,], dtype=f16, space=TMEM        ; v
⟦ALLOC⟧ GR13, shape=[B,C',H',W'], dtype=f16, space=TMEM ; W out

⟡    GR13, GR10, GR11, TLV(stride=2,pad=1)
⨀    GR14, GR13, GR12
≥     GR15, GR14, IMM(θ=0.75)
→     label_print, GR15
⟲    GR14, GR14, IMM(seed=42)
→     label_done, GRZ
label_print:
⟦IO⟧ "print", GR14
label_done:
⟦RET⟧ GR14

12) Error Model & Traps

Code                                            Meaning                                 Action
E0                                              Type mismatch                           Set GRF.E, halt beam or raise to caller
E1                                              Shape mismatch                          Ditto; optional auto-broadcast if flag set
E2
Divide by zero
Policy TLV: {NaG, clamp, raise}
E3
Rule violation
Set ⚖ + E; jump to handler
E4
Timeout/deadlock
Set E; emit HUD; optional auto-collapse
E5
No resource
Alloc failure; retry/back-off via ⟦SCHED⟧


13) Encoding Examples (TLV)
	•	IMM_SCALAR(f32) → 0x01 | len=4 | bytes
	•	AXIS(u8) → 0x02 | len=1 | axis
	•	TAG_ENTANGLE_ID(u128) → 0x10 | len=16 | uuid
	•	SQI_MASK(u8) → 0x11 | len=1 | mask
	•	MEM_ORDER(u8) → 0x12 | len=1 | {0..3}

⸻

14) Implementation Notes (Phase-1 → Phase-3)
	•	Phase-1 (Now, on CPUs/GPUs)
	•	Atomic math → NumPy/PyTorch ops
	•	∑/⊠/⟡ → BLAS/cuDNN via ⟦MAP⟧
	•	∇ → SymPy/Autograd
	•	Entanglement & flags → runtime metadata + logs
	•	Determinism via single-thread scheduling mode
	•	Phase-2 (Hybrid JIT)
	•	Hot glyphs JIT-compiled to fused kernels
	•	Persistent memory pools (⟦PIN⟧)
	•	Beam scheduler maps to streams/threads
	•	Phase-3 (Native sTPU)
	•	Macro-op decode for composite glyphs
	•	Tensor tiles + glyph metadata SRAM
	•	On-chip HUD/KG event lanes
	•	Entanglement crossbar + ⧖ barrier fabric

⸻

15) “Datasheet Page” Template (apply to any new opcode)

NAME (Glyph, Opcode)
Form: …
Description: …
Inputs: …
Outputs: …
Flags: …
Pseudocode:

...

Encoding: opcode, operands, required TLVs
Trace (example): …
Exceptions: …
Notes: impl details & Phase-1/2/3 mapping

⸻

Appendix A — Fully Detailed Pages Included Above
	•	ATOMIC: ⊕, ⊖, ⊗, ÷, ↔, ≠, ≥/≤, ∇, ⟲, →, ⊙, ⊻, ¬, |·|, √
	•	COMPOSITE: ∑, ∫, ⧖, ⟡, ⨀, ⊞, ⊠, 𝕊, ⧫, ⟡⟲, ↻, ⫴, ⫽, ⤧
	•	META: ⟦ALLOC⟧, ⟦FREE⟧, ⟦IO⟧, ⟦FORK⟧, ⟦JOIN⟧, ⟦SCHED⟧, ⟦RULE⟧, ⟦KG⟧, ⟦HUD⟧, ⟦NET⟧, ⟦CALL⟧, ⟦RET⟧, ⟦MAP⟧, ⟦PIN⟧, ⟦UNPIN⟧

⸻

16) What you can do right now
	•	Compiler: map CodexLang to these opcodes (Phase-1 backend).
	•	Runtime: implement bytecode loader, TLV parser, flags engine, and a first-cut beam scheduler.
	•	JIT: wire ⟦MAP⟧ to NumPy/BLAS/cuDNN for ∑/⊠/⟡.
	•	Tracing: push ⟦HUD⟧ & ⟦KG⟧ events so GHX/KnowledgeGraphWriter see full execution.

If you want, I can turn this into a Markdown/PDF manual with an index and per-opcode anchors, or generate stub code for a reference interpreter (bytecode parser + dispatcher + flags + a few ops) so your team can start executing this ISA immediately.

