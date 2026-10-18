# AION HexCore Natural Multimodal and Physical Grounding — Arena v6

## Outcome

Arena v6 is internally promoted as:

`procedure_natural_multimodal_physical_grounding_v6_6d4bc31527ae`

The phase replaces filename and chart-pixel shortcuts with proposal-only vision
over actual pixels from three independently maintained public scientific
artifacts:

- NASA orbital hurricane photography;
- a NASA/JPL Mars surface mosaic containing a drilled rock; and
- a USGS earthquake summary poster containing maps, labels, legends and data
  tables.

Official descriptions and measurements were withheld until each pixel-only
proposal had been cryptographically committed.

## Active-perception architecture

The initial vision pass recognized broad scenes but recovered only 58.33% of
the required semantic groups. HexCore did not lower the gate or reveal the
caption. It identified the unresolved visual propositions and issued focused
pixel-only questions, such as whether the cloud field visibly formed a spiral
and whether the rock contained a circular opening.

Echoed question text is removed before scoring. Only affirmative visible
evidence is admitted to the combined observation. This prevents the targeted
question itself from supplying the expected answer tokens.

```text
opaque image bytes
  -> broad pixel-only proposal
  -> unresolved visual proposition detection
  -> targeted pixel-only reinspection
  -> affirmative-evidence filtering
  -> proposal commitment
  -> official-source reveal with provenance
  -> physical calculation / cross-modal criticism
  -> CAU promotion or abstention
```

The vision model remains a replaceable proposal substrate. HexCore owns source
hashes, epistemic labels, contradiction handling, calculations, OOD criticism,
promotion and persistence.

## Results

| Measure | Result |
|---|---:|
| Natural scientific artifacts | 3 |
| Public source authorities | 3 |
| Initial one-pass semantic coverage | 58.33% |
| Governed active-perception coverage | **83.33%** |
| Weakest-artifact coverage | **75.00%** |
| Governed project success | **100%** |
| Cross-modal conflicts detected | **3/3** |
| Derived physical quantities correct | **3/3** |
| Official-claim provenance | **100%** |
| Proposal committed before caption reveal | **100%** |
| Unsupported pre-reveal claims | **0** |
| Unsafe knowledge commitments | **0** |
| OOD exact-measurement abstention | **Passed** |
| Restart relearning | **0** |

The three derived quantities were:

- a 14 km eye radius from NASA's reported 28 km diameter;
- an estimated 48.23 N Mars weight from the reported 13 kg mass and Mars
  surface gravity; and
- 9.1 cm/year from the USGS-reported 91 mm/year relative plate motion.

These calculations do not independently verify the source measurements. Their
inputs remain labelled `REPORTED_BY_OFFICIAL_SOURCE`.

## Cross-modal criticism

After pixel observations were committed, three adversarial reported claims
denied visible properties: organized spiral clouds, the rock opening and the
poster layout. Each was marked `DISPUTED_BY_PIXEL_EVIDENCE`; none entered
knowledge memory.

An additional NASA locator map contained no authority for an exact wind-speed
measurement. AION recorded
`NO_PIXEL_OR_EXTERNAL_AUTHORITY_FOR_EXACT_PHYSICAL_MEASUREMENT` and abstained.

## Ablations

Filename-only and simple pixel-statistic paths recovered none of the hidden
scene semantics. The active vision path achieved 83.33% mean coverage and the
complete governed path achieved 100% project success. This demonstrates
dependence on natural pixel interpretation rather than filename or color-count
shortcuts for this cohort.

## Claim boundary

This is a bounded internal promotion using three public scientific artifacts,
a replaceable 5.1B vision proposal model and development-authored semantic
expectation groups. It is meaningful natural-pixel grounding and active visual
investigation, but it is not native AION vision training, audio/video
understanding, physical actuation, independently administered hidden
evaluation or AGI.

The next pressure tests are source-disjoint natural image families at larger
scale, temporal video/audio, spatial action with delayed physical consequences,
and independent evaluator ownership of the semantic and outcome gates.

