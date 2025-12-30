from pathlib import Path

REPO = Path("/workspaces/COMDEX")

FILES = {
  # ----------------------------
  # VOL IV directories + README
  # ----------------------------
  "docs/Artifacts/VolIV/README.md": """\
# Volume IV Artifacts (canonical)

Volume IV: Information Theory — Coherence as Information

## Canonical paths
- Paper (spec mirror): `docs/Artifacts/VolIV/proofs/VolIV_Coherence_As_Information_v0_1.tex`
- Build manifest: `docs/Artifacts/VolIV/build/VOLIV_PIPELINE_MANIFEST.yaml`
- Mapping: `docs/Artifacts/VolIV/build/VOL0_VOLIV_MAPPING.json`
- Scene: `docs/Artifacts/VolIV/qfc/VOLIV_INFORMATION_METRIC.scene.json`
- Acceptance thresholds: `docs/Artifacts/VolIV/build/VOLIV_ACCEPTANCE_THRESHOLDS.yaml`

## Dependencies (Truth Chain)
- SRK-8 repaired ledger: `docs/Artifacts/SRK8/ledger/theorem_ledger_repaired.jsonl`
- SRK-12 spec mirror: `docs/Artifacts/SRK12/proofs/SRK12_Photon_Algebra_v1_1.tex`
- PAEV-10 Born rule track: `docs/rfc/Photon Algebra Experimental Validation/Photon Algebra Experimental Validation Suite (PAEV-10)/Born rule/`
""",

  # ----------------------------
  # Build surface
  # ----------------------------
  "docs/Artifacts/VolIV/build/VOLIV_PIPELINE_MANIFEST.yaml": """\
# VOLIV_PIPELINE_MANIFEST.yaml
# Volume IV build/lock surface: metric definitions + QFC scene hook.
vol: Volume IV
title: Coherence as Information
version: v0.1
lock_id: VOL-IV-INFO-COHERENCE-v0.1
status: DRAFT_LOCKABLE
date: 2025-12-30

depends_on:
  truth_chain: docs/Artifacts/TRUTHCHAIN/TRUTHCHAIN_v0.2.tex
  srk8_ledger_repaired: docs/Artifacts/SRK8/ledger/theorem_ledger_repaired.jsonl
  srk12_spec: docs/Artifacts/SRK12/proofs/SRK12_Photon_Algebra_v1_1.tex

artifacts:
  paper: docs/Artifacts/VolIV/proofs/VolIV_Coherence_As_Information_v0_1.tex
  scene: docs/Artifacts/VolIV/qfc/VOLIV_INFORMATION_METRIC.scene.json
  thresholds: docs/Artifacts/VolIV/build/VOLIV_ACCEPTANCE_THRESHOLDS.yaml
  mapping: docs/Artifacts/VolIV/build/VOL0_VOLIV_MAPPING.json

symbols_in_force:
  collapse_selection: "\\\\mu"
  grad_reserved: "\\\\nabla"
  born_weight: "\\\\Delta"

repro:
  deterministic_replay_required: true
""",

  "docs/Artifacts/VolIV/build/VOL0_VOLIV_MAPPING.json": """\
{
  "vol0_reserved": {
    "grad": "\\\\nabla",
    "collapse_selection": "\\\\mu",
    "born_weight": "\\\\Delta"
  },
  "voliv_symbols": {
    "superpose": "\\\\oplus",
    "entangle": "\\\\leftrightarrow",
    "recurse": "\\\\circlearrowleft",
    "measure": "\\\\mu",
    "project": "\\\\pi",
    "bornw": "\\\\Delta",
    "grad": "\\\\nabla",
    "info": "\\\\mathcal{I}",
    "decoherence": "D_{\\\\phi}",
    "coherence_functional": "C_{+}"
  },
  "notes": [
    "MUST: use \\\\mu for measurement/collapse/selection.",
    "MUST: reserve \\\\nabla for geometric gradient/divergence only.",
    "MUST: use \\\\Delta for Born weight / intensity; it is not collapse."
  ]
}
""",

  "docs/Artifacts/VolIV/build/VOLIV_ACCEPTANCE_THRESHOLDS.yaml": """\
# VOLIV_ACCEPTANCE_THRESHOLDS.yaml
# Default acceptance checks for Volume IV (Metric Bridge).

symbol_alignment:
  must_use_mu_for_selection: true
  must_reserve_nabla_for_gradient: true
  must_use_delta_for_born_weight: true

identity_checks:
  # Identity to support: I = 1 - D_phi
  I_range: [0.0, 1.0]
  Dphi_range: [0.0, 1.0]
  require_I_plus_Dphi_equals_1_within_abs_tol: 1.0e-12

thermo_bridge:
  # Operational (runtime/audit) acceptance, not a universal physics claim.
  require_entropy_decrease_implies_info_increase: true
  min_deltaS: -1.0e-6
  min_deltaI:  1.0e-6

coherence_functional:
  # C_+ is the probability-weighting functional used downstream (PAEV-A3).
  require_Cplus_nonnegative: true
  require_Cplus_monotone_in_I: true

qfc_scene:
  name: VOLIV_INFORMATION_METRIC
  metrics:
    - COHERENCE_GAIN
    - ENTROPY_TO_INFO_SLOPE
""",

  # ----------------------------
  # QFC scene spec (for your TSX)
  # ----------------------------
  "docs/Artifacts/VolIV/qfc/VOLIV_INFORMATION_METRIC.scene.json": """\
{
  "scene": "VOLIV_INFORMATION_METRIC",
  "goal": "Visualize conversion of high-entropy phase noise into phase-locked coherence and verify I = 1 - D_phi.",
  "setup": {
    "n_oscillators": 256,
    "initial_state": "WHITE_NOISE",
    "target_state": "PHASE_LOCKED",
    "phase_distribution": "wrapped_normal",
    "seed": 42
  },
  "definitions": {
    "D_phi": "normalized phase dispersion in [0,1] computed from circular variance",
    "I": "information-as-coherence, defined as I = 1 - D_phi",
    "C_plus": "coherence functional used as downstream weighting; must be monotone in I"
  },
  "stages": [
    "initialize_white_noise",
    "apply_phase_lock_controller",
    "measure_D_phi",
    "compute_I",
    "compute_C_plus",
    "emit_metrics"
  ],
  "metrics": [
    { "name": "COHERENCE_GAIN", "definition": "I_final - I_initial" },
    { "name": "ENTROPY_TO_INFO_SLOPE", "definition": "-DeltaS / DeltaI (operational audit metric)" }
  ],
  "acceptance": {
    "I_bounds": [0, 1],
    "D_phi_bounds": [0, 1],
    "identity_abs_tol": 1e-12
  },
  "tsx_hint": "QFCInformationMetric.tsx"
}""",

  # ----------------------------
  # Volume IV paper (house style + Truth Chain aligned)
  # ----------------------------
  "docs/Artifacts/VolIV/proofs/VolIV_Coherence_As_Information_v0_1.tex": r"""\documentclass[11pt,a4paper]{article}

% --- Tessaris house style ---
\usepackage[a4paper,margin=1in]{geometry}
\usepackage[T1]{fontenc}
\usepackage{microtype}
\usepackage{newtxtext,newtxmath}
\usepackage{xurl}
\usepackage[hidelinks]{hyperref}

% --- Math / layout ---
\usepackage{amsmath,amssymb,mathtools}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{ragged2e}
\usepackage{enumitem}

\newcolumntype{Y}{>{\RaggedRight\arraybackslash}X}

% --- Truth Chain macros (normative) ---
\newcommand{\superpose}{\oplus}
\newcommand{\entangle}{\leftrightarrow}
\newcommand{\recurse}{\circlearrowleft}
\newcommand{\bornw}{\Delta}   % Born weight / intensity (NOT collapse)
\newcommand{\measure}{\mu}    % measurement / collapse / selection
\newcommand{\project}{\pi}
\newcommand{\evolve}{\Rightarrow}
\newcommand{\grad}{\nabla}    % RESERVED: geometric gradient/divergence only

% --- Volume IV symbols ---
\newcommand{\Info}{\mathcal{I}}
\newcommand{\Dphi}{D_{\phi}}
\newcommand{\Cplus}{C_{+}}

\title{\textbf{Volume IV: Information Theory — Coherence as Information}\\[4pt]
\large The Metric Bridge for Governed Selection and Downstream Unified Equations (v0.1)}
\author{Kevin Robinson \;\;|\;\; Tessaris AI}
\date{December 30, 2025}

\begin{document}
\maketitle

\begin{abstract}
Volume IV is the pivot document in the Tessaris ``Proof of Chain'' strategy.
SRK-12 established a mechanism: symbolic operators map to phase-native photonic interference.
This volume establishes a metric: \emph{information} is defined as phase coherence.
The key identity is $\Info = 1 - \Dphi$, where $\Dphi \in [0,1]$ is a normalized phase-dispersion (decoherence) factor.
We also define the coherence functional $\Cplus$, which is used downstream to weight governed selection and probability tests (e.g.\ PAEV-A3).
\end{abstract}

\section{Normative Scope (Truth Chain)}
This document is \textbf{normative} only for:
\begin{itemize}[noitemsep]
\item defining information as phase coherence (the $\Info$ metric),
\item defining $\Dphi$ and $\Cplus$ as reproducible functionals,
\item specifying the canonical artifact paths and QFC scene for verification.
\end{itemize}
It does \emph{not} claim universal physical truth beyond the operational domain of Tessaris kernels.

\subsection*{Definitions in force}
\begin{itemize}[noitemsep]
\item \textbf{Selection/collapse:} MUST use $\measure$.
\item \textbf{Gradient:} $\grad$ is RESERVED and MUST NOT be treated as selection/collapse.
\item \textbf{Born weight:} MUST use $\bornw$ as intensity/selection weight; it is not collapse.
\end{itemize}

\section{Why This Volume Exists (Pivot Point)}
SRK-12 provided the \emph{gearbox}: phase-native fusion $\fuse{\phi}$ and governed selection mechanics.
Volume IV provides the \emph{metric}: it explains what the runtime is maximizing/minimizing when it “stabilizes meaning.”
Concretely, it makes coherence measurable as information.

\section{Core Identity: \texorpdfstring{$\Info = 1 - \Dphi$}{I = 1 - Dphi}}
\subsection{Phase dispersion}
Let $\phi$ denote the phase variable of a branch or oscillator ensemble.
Define $\Dphi \in [0,1]$ as a normalized dispersion measure (implementation MUST choose a bounded circular statistic).
A common choice is circular variance; other bounded equivalents are acceptable if explicitly stated and stable.

\subsection{Information as coherence}
Define:
\[
\Info \triangleq 1 - \Dphi.
\]
By construction, $\Info \in [0,1]$.
High information corresponds to phase-lock (low dispersion), and low information corresponds to decoherence (high dispersion).

\section{Thermodynamic Bridge (Operational)}
For auditability, Tessaris treats the following as an \emph{operational invariant} to be checked in controlled runtime tests:
\[
\Delta S < 0 \implies \Delta \Info > 0,
\]
under a stated energy bookkeeping regime (e.g.\ constant total injected energy per episode).
This is used as a sanity test for “coherent intent” behavior in systems that implement feedback stabilization.
It is not presented as a universal physics law without domain constraints.

\section{Coherence Functional \texorpdfstring{$\Cplus$}{C+} (Downstream Weight)}
Define $\Cplus$ as a nonnegative weighting functional, monotone in $\Info$, used downstream to bias selection/measurement.
Minimal requirements:
\begin{itemize}[noitemsep]
\item $\Cplus \ge 0$ everywhere,
\item $\Info_1 \le \Info_2 \Rightarrow \Cplus(\Info_1) \le \Cplus(\Info_2)$,
\item $\Cplus$ is stable under deterministic replay.
\end{itemize}
A simple family is $\Cplus(\Info)=\Info^p$ for $p\ge 1$, but implementations MAY choose alternatives with equivalent monotonicity.

\section{Reproducibility Hooks (Canonical Paths)}
\begin{itemize}[noitemsep]
\item QFC scene:
\texttt{docs/Artifacts/VolIV/qfc/VOLIV\_INFORMATION\_METRIC.scene.json}
\item Thresholds:
\texttt{docs/Artifacts/VolIV/build/VOLIV\_ACCEPTANCE\_THRESHOLDS.yaml}
\item Build manifest:
\texttt{docs/Artifacts/VolIV/build/VOLIV\_PIPELINE\_MANIFEST.yaml}
\item Dependencies:
\texttt{docs/Artifacts/SRK8/ledger/theorem\_ledger\_repaired.jsonl},
\texttt{docs/Artifacts/SRK12/proofs/SRK12\_Photon\_Algebra\_v1\_1.tex}
\end{itemize}

\vfill
\noindent\rule{\linewidth}{0.4pt}

\noindent
Lock ID: VOL-IV-INFO-COHERENCE-v0.1\\
Status: DRAFT\\
Maintainer: Tessaris AI\\
Author: Kevin Robinson.

\end{document}
""",
}

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

for rel, txt in FILES.items():
    write(REPO / rel, txt)

print(f"Wrote {len(FILES)} files under docs/Artifacts/VolIV/")