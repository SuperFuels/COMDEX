from pathlib import Path

REPO = Path("/workspaces/COMDEX")

FILES = {
  # ----------------------------
  # Build / lock surface
  # ----------------------------
  "docs/Artifacts/SRK12/build/SRK12_VALIDATION_MANIFEST.yaml": """\
# SRK12_VALIDATION_MANIFEST.yaml
# SRK-12 Validation Note (PAEV-10 Born rule binding) — lock surface
srk: SRK-12
doc: SRK-12 Validation Note / Appendix
lock_id: SRK-12-VALIDATION-NOTE-v1.1
status: LOCKED_AND_VERIFIED
date: 2025-12-30

depends_on:
  truth_chain: docs/Artifacts/TRUTHCHAIN/TRUTHCHAIN_v0.2.tex
  srk12_spec_mirror: docs/Artifacts/SRK12/proofs/SRK12_Photon_Algebra_v1_1.tex
  srk8_ledger_repaired: docs/Artifacts/SRK8/ledger/theorem_ledger_repaired.jsonl

evidence_track:
  paev10_born_rule:
    path: "docs/rfc/Photon Algebra Experimental Validation/Photon Algebra Experimental Validation Suite (PAEV-10)/Born rule/"
    required: true

artifacts:
  note_tex: docs/Artifacts/SRK12/validation/SRK12_Validation_Note_v1_1.tex
  thresholds: docs/Artifacts/SRK12/validation/SRK12_ACCEPTANCE_THRESHOLDS.yaml
  replay_schema: docs/Artifacts/SRK12/ledger/SRK12_GOVERNED_SELECTION_TRACE_SCHEMA.json
  link_note: docs/Artifacts/SRK12/validation/PAEV10_BORN_RULE_LINK.md

normative_symbols:
  collapse_selection: "\\\\mu"
  grad_reserved: "\\\\nabla"
  born_weight: "\\\\Delta"

repro:
  deterministic_replay_required: true
""",

  "docs/Artifacts/SRK12/validation/SRK12_ACCEPTANCE_THRESHOLDS.yaml": """\
# SRK12_ACCEPTANCE_THRESHOLDS.yaml
# Default acceptance thresholds for SRK-12 governed selection validation.

symbols:
  must_use_mu_for_selection: true
  must_reserve_nabla_for_gradient: true
  must_use_delta_for_born_weight: true

deterministic_replay:
  prob_abs_tol: 1.0e-12
  prob_rel_tol: 1.0e-10
  require_same_selected_branch: true
  determinism_ratio_min: 0.999999999999  # 1 - 1e-12

born_rule_agreement:
  # Compare predicted distribution vs observed empirical frequencies.
  trials_min: 10000
  total_variation_max: 0.02
  kl_divergence_max: 0.01

policy_modulation:
  # If a branch is tagged Contradiction and receives negative status_bonus,
  # it MUST be suppressed before final selection.
  contradiction_prob_after_max: 1.0e-9
  must_renormalize_after_modulation: true

ledger_dependency:
  # SRK-12 MUST bind to SRK-8 repaired ledger for consumed semantics.
  require_srk8_repaired_ledger_present: true
  require_nonempty_hashes: true
""",

  "docs/Artifacts/SRK12/validation/PAEV10_BORN_RULE_LINK.md": """\
# PAEV-10 Born rule — Canonical Evidence Link (SRK-12)

**Canonical evidence track (repo path):**
`docs/rfc/Photon Algebra Experimental Validation/Photon Algebra Experimental Validation Suite (PAEV-10)/Born rule/`

This SRK-12 validation note treats the above directory as the **single source of truth**
for Born-rule correspondence evidence, including:
- analytic checks (closed-form expectations),
- Monte Carlo / repeated trials (empirical frequency vs predicted probability),
- replay trace artifacts (WaveCapsule + policy gates + renormalization).

If you later reorganize the PAEV folder, update:
- `docs/Artifacts/SRK12/build/SRK12_VALIDATION_MANIFEST.yaml`
- Truth Chain record for SRK-12 validation note (artifact paths)
""",

  # ----------------------------
  # The actual Validation Note (LaTeX)
  # ----------------------------
  "docs/Artifacts/SRK12/validation/SRK12_Validation_Note_v1_1.tex": r"""\documentclass[11pt,a4paper]{article}

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

% --- Truth Chain / Vol0 normalized macros ---
\newcommand{\superpose}{\oplus}
\newcommand{\entangle}{\leftrightarrow}
\newcommand{\recurse}{\circlearrowleft}
\newcommand{\bornw}{\Delta}   % Born weight / intensity (NOT collapse)
\newcommand{\measure}{\mu}    % measurement / collapse / selection
\newcommand{\project}{\pi}
\newcommand{\evolve}{\Rightarrow}
\newcommand{\grad}{\nabla}    % RESERVED: gradient/divergence only

% --- SRK-12 extras ---
\newcommand{\Sig}{\Sigma}
\newcommand{\Eval}{\mathrm{Eval}}
\newcommand{\fuse}[1]{\mathbin{\bowtie\!\left[#1\right]}}
\newcommand{\botexpr}{\bot}

\title{\textbf{SRK-12 Validation Note / Appendix}\\[4pt]
\large Governed Selection (Born Rule + Policy Modulation) Bound to PAEV-10 Evidence Track (v1.1)}
\author{Kevin Robinson \;\;|\;\; Tessaris AI}
\date{December 30, 2025}

\begin{document}
\maketitle

\begin{abstract}
This note formalizes the validation relationship between (i) SRK-12 governed selection
(Born weighting + policy modulation + renormalization + deterministic replay) and
(ii) the PAEV-10 Born rule evidence track.
It defines a deterministic replay trace schema, acceptance thresholds, and the canonical artifact paths
required to claim SRK-12 selection correctness \emph{within the Tessaris Truth Chain}.
\end{abstract}

\section{Scope and Normative References}
This document is \textbf{normative} for SRK-12 validation within the Truth Chain.
It is concerned with \emph{replayable correctness} and \emph{evidence binding}, not new operator invention.

\begin{itemize}[noitemsep]
\item Truth Chain manifest: \texttt{docs/Artifacts/TRUTHCHAIN/TRUTHCHAIN\_v0.2.tex}
\item SRK-12 spec mirror: \texttt{docs/Artifacts/SRK12/proofs/SRK12\_Photon\_Algebra\_v1\_1.tex}
\item SRK-8 repaired ledger dependency: \texttt{docs/Artifacts/SRK8/ledger/theorem\_ledger\_repaired.jsonl}
\item PAEV-10 Born rule evidence track: \texttt{docs/rfc/Photon Algebra Experimental Validation/Photon Algebra Experimental Validation Suite (PAEV-10)/Born rule/}
\end{itemize}

\section{Definitions in Force (Truth Chain)}
\begin{itemize}[noitemsep]
\item \textbf{Selection:} MUST use $\measure$.
\item \textbf{Gradient:} $\grad$ is RESERVED and MUST NOT be treated as selection/collapse.
\item \textbf{Born weight:} MUST use $\bornw$ as intensity/selection weight; it is not collapse.
\end{itemize}

\section{What is Being Validated}
SRK-12 governed selection is the map from a WaveCapsule branch set to one discrete outcome:
\begin{enumerate}[noitemsep]
\item Compute Born weights via $\bornw(\sigma) \equiv |\alpha(\sigma)|^2$.
\item Compute base probabilities $P(\sigma)$ by normalization.
\item Apply policy modulation (e.g.\ \texttt{status\_bonus}, tags).
\item Renormalize to obtain $P'(\sigma)$.
\item Select a branch, and emit a trace sufficient for deterministic replay.
\end{enumerate}

This note specifies how the above MUST be tied to PAEV-10 Born rule evidence and what constitutes acceptance.

\section{Evidence Track Binding (PAEV-10)}
The directory
\[
\texttt{docs/rfc/Photon Algebra Experimental Validation/Photon Algebra Experimental Validation Suite (PAEV-10)/Born rule/}
\]
is the canonical evidence track for probability resolution. SRK-12 validation MUST:
\begin{itemize}[noitemsep]
\item reference this path unchanged (or update the Truth Chain record if moved),
\item cite at least one analytic and one empirical frequency check from within the track,
\item include replay traces for the runs that generated empirical frequencies.
\end{itemize}

\section{Deterministic Replay Trace (Normative)}
Every governed selection MUST emit a replay trace that conforms to:
\[
\texttt{docs/Artifacts/SRK12/ledger/SRK12\_GOVERNED\_SELECTION\_TRACE\_SCHEMA.json}.
\]
The trace MUST be sufficient to recompute:
\begin{itemize}[noitemsep]
\item $P(\sigma)$ from amplitudes and phases (as applicable),
\item policy modulation inputs (e.g.\ \texttt{status\_bonus}, policy tags),
\item $P'(\sigma)$ after renormalization,
\item the selected branch,
\item the reported \texttt{SELECTION\_DETERMINISM\_RATIO}.
\end{itemize}

\section{Acceptance Criteria (Default Thresholds)}
Default thresholds are defined in:
\[
\texttt{docs/Artifacts/SRK12/validation/SRK12\_ACCEPTANCE\_THRESHOLDS.yaml}.
\]
An implementation is accepted when all criteria below hold.

\subsection{A0: Symbol alignment}
The runtime and documents MUST use $\measure$ for selection and MUST reserve $\grad$ for gradient only.
Born weight MUST be expressed as $\bornw$.

\subsection{A1: Ledger dependency integrity}
If SRK-12 consumes SRK-8 semantics, it MUST reference the SRK-8 repaired ledger and MUST NOT rely on empty hashes.

\subsection{A2: Deterministic replay correctness}
Given a recorded trace, recomputed probabilities MUST match within configured tolerances, and the selected branch MUST match.
The determinism ratio MUST meet the configured minimum.

\subsection{A3: Born rule agreement (empirical)}
For sufficiently many trials, empirical frequencies MUST match predicted probabilities within configured bounds
(e.g.\ total variation distance and KL divergence thresholds).

\subsection{A4: Policy modulation safety}
A branch tagged contradictory with negative modulation MUST be suppressed below the configured maximum probability
(or eliminated prior to selection), and renormalization MUST occur.

\section{Canonical Artifacts (Lock Surface)}
\begin{itemize}[noitemsep]
\item Thresholds: \texttt{docs/Artifacts/SRK12/validation/SRK12\_ACCEPTANCE\_THRESHOLDS.yaml}
\item Replay schema: \texttt{docs/Artifacts/SRK12/ledger/SRK12\_GOVERNED\_SELECTION\_TRACE\_SCHEMA.json}
\item Evidence link note: \texttt{docs/Artifacts/SRK12/validation/PAEV10\_BORN\_RULE\_LINK.md}
\item Validation manifest: \texttt{docs/Artifacts/SRK12/build/SRK12\_VALIDATION\_MANIFEST.yaml}
\end{itemize}

\vfill
\noindent\rule{\linewidth}{0.4pt}

\noindent
Lock ID: SRK-12-VALIDATION-NOTE-v1.1\\
Status: LOCKED \& VERIFIED\\
Maintainer: Tessaris AI\\
Author: Kevin Robinson.

\end{document}
""",

  "docs/Artifacts/SRK12/validation/README.md": """\
# SRK-12 Validation Note / Appendix (canonical)

This folder binds SRK-12 governed selection to the PAEV-10 Born rule evidence track.

Canonical files:
- `SRK12_Validation_Note_v1_1.tex`
- `SRK12_ACCEPTANCE_THRESHOLDS.yaml`
- `PAEV10_BORN_RULE_LINK.md`

Normative replay schema (shared with SRK-12):
- `docs/Artifacts/SRK12/ledger/SRK12_GOVERNED_SELECTION_TRACE_SCHEMA.json`
""",
}

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

for rel, txt in FILES.items():
    write(REPO / rel, txt)

print(f"Wrote {len(FILES)} files under docs/Artifacts/SRK12/validation/ and build/")