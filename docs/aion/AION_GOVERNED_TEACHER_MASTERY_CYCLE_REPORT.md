# AION Governed Teacher and Mastery Cycle

## Purpose

This stage converts the conceptual teacher--learner--examiner design into an
executable learning control plane.  A replaceable teacher may recommend what a
subject contains and how to practise it.  The teacher is not allowed to decide
whether AION has learned the subject.  Promotion remains owned by executable
outcomes, sealed assessment, HexCore and CAU.

Promoted procedure:

`procedure_governed_teacher_python_core_cycle_v1`

## Architecture

The operating cycle is:

```text
mastery gap
  -> cached teacher curriculum proposal
  -> examiner commitment before study
  -> practice and public feedback
  -> sealed knowledge/practical evaluation
  -> narrow failure attribution
  -> targeted remediation
  -> fresh sealed variant
  -> cross-domain transfer
  -> restart reconstruction
  -> bounded certificate + delayed retest due
```

The `TeacherBroker` exposes a replaceable provider boundary.  Its first local
run uses a retained offline curriculum so operation does not depend on a remote
model.  It also consulted the installed `gemma3:1b` model through Ollama in a
live 4.16-second advisory call. Gemma proposed nine modules, nine projects and
nine common failure modes. The response was content-addressed and cached, and
no exam material was shared.

The curriculum critic retained the response only as a supplement: it identified
useful object-oriented, database and system-design themes, but found that the
proposal did not adequately specify packaging, typing/contracts,
errors/resources, transfer or delayed retention. Gemma could therefore neither
replace the core curriculum nor authorize the certificate. A future OpenAI
provider can enter through the identical proposal-only boundary.

The Python Core curriculum contains twelve modules: fundamentals; data and
algorithms; modules and packaging; typing and contracts; errors and resources;
testing and debugging; persistence; concurrency; performance; security;
architecture; and unfamiliar-repository transfer.  The existence of a module
does not constitute evidence that it has been mastered.

## Assessment authority

The assessment contract is hashed before candidate execution.  Its weighted
categories are knowledge (15%), construction (30%), debugging (20%), testing
and security (15%), transfer (15%), and restart retention (5%).  The overall
threshold is 90%, but category minimums and hard gates also apply.  Security is
an absolute gate.

The first apparently valid implementation passed its public exercise but was
rejected by the sealed examiner because Python's `bool` is a subclass of
`int`.  The input contract required integers but not booleans.  AION attributed
the failure to input semantics, remediated only that subskill, and passed a new
sealed execution.  The curriculum was not restarted from the beginning.

The resulting invariant transferred into a source-disjoint account batch
processor: invalid or overdrawn batches were rejected without corrupting the
retained balance.  Existing historical Git plus hidden-test evidence supplied
the debugging authority.  Six malicious variants involving dynamic execution,
process launch, networking and destructive file operations were rejected
before execution.

## Results

| Measure | Result |
|---|---:|
| Curriculum modules proposed | 12 |
| Exam committed before candidate execution | Passed |
| Initial plausible challenger rejected | Passed |
| Narrow failure attribution | Passed |
| Targeted remediation | Passed |
| Fresh sealed retest | Passed |
| Weighted cycle score | 100% |
| Required threshold | 90% |
| Malicious programs rejected | 6/6 |
| Source-disjoint transfer | Passed |
| Restart reconstruction | Passed |
| Unsafe programs executed | 0 |
| Live repository writes | 0 |
| Objective mutations | 0 |

The recorded certificate is
`certificate_python_core_governed_v1`.  Its level is
`operational_bounded`, with work readiness limited to bounded Python work under
executable verification.  It certifies no Python specialisation, expert status
or whole-language mastery.  A genuinely elapsed retention assessment remains
scheduled; immediate process reconstruction is not represented as multi-week
retention.

## Mastery-registry integration

The certificate artifact is now an evidence source for the existing North Star
mastery registry.  A capability query still answers **no** to "Have you mastered
Python?" and reports the outstanding requirements: broad unfamiliar projects,
multi-month retention, independently controlled professional outcomes,
full-subject failure recovery, teaching/leadership and invention outside the
development distribution.

## Claim boundary and next work

This promotes the learning control plane and one bounded assessment receipt.
The curriculum fallback, practical problem family and examiner were engineered.
It does not prove autonomous curriculum discovery, comprehensive Python
competence, expertise, mastery or AGI.

The next stages are:

1. connect a real Gemma/OpenAI teacher proposal through the same cached,
   proposal-only broker and compare it with the retained curriculum;
2. expand Python Core into multiple source-disjoint construction, debugging,
   concurrency, packaging and performance projects;
3. run an elapsed retention retest with fresh tasks rather than solution replay;
4. issue separate application-specialisation certificates; and
5. reuse the same subject-agnostic cycle for a qualitatively different domain
   whose authority is not a programming runtime.
