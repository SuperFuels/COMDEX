# HexCore Arena v7: Temporal Multimodal Action

## Outcome

Arena v7 is internally promoted as
`procedure_temporal_multimodal_action_v7_2a4710a57e8d`.

The stage extends Arena v6 from isolated natural images into ordered visual and
acoustic time.  It uses two official NASA videos and one official USGS seismic
recording.  Proposals are committed before official explanatory claims are
revealed.  Unsupported exact identities are quarantined rather than accepted.

## Architecture

Video is represented by ordered, source-hashed image frames.  A replaceable
vision proposal model describes persistence, change and a qualitative
next-frame prediction.  HexCore independently checks chronology by comparing
the adjacent-frame continuity cost

\[
C(\pi)=\frac{1}{T-1}\sum_{t=1}^{T-1}
\operatorname{MAE}(I_{\pi(t+1)},I_{\pi(t)}).
\]

A deliberately broken order must have greater cost than the source order; when
chronology is broken, forecasting abstains.

Audio is not misrepresented as native listening.  The official waveform is
converted into a spectrogram for semantic proposal and into five-second RMS
windows for measurement.  The initial policy spent all four costly inspections
inside the proposed regions and found only one of the four strongest events.
CAU rejected that run.  The promoted policy uses hierarchical sensing:

1. scan every window using a low-cost energy measurement;
2. allocate two detailed inspections to the semantic hypothesis;
3. reserve two detailed inspections for the strongest unexplained windows; and
4. retain the spectrogram proposal, measurement allocation and official reveal
   as separate provenance-bearing records.

With coarse cost \(c_s=0.05\), detailed cost \(c_d=1\), \(N=39\) windows and
\(k=4\) detailed inspections, the active cost is

\[
C_{\mathrm{active}}=Nc_s+kc_d=5.95,
\qquad C_{\mathrm{exhaustive}}=Nc_d=39.
\]

## Sealed result

| Measure | Result |
|---|---:|
| Public temporal sources / authorities | 3 / 3 |
| Video temporal semantic accuracy | 100% |
| Weakest video accuracy | 100% |
| Broken chronologies detected | 2 / 2 |
| Derived temporal quantities correct | 2 / 2 |
| Seismic spectral semantic accuracy | 100% |
| Strongest-event coverage | 75% |
| Audio measurement-cost reduction | 84.74% |
| Video frame reduction | 33.33% |
| Governed project success | 100% |
| Unsupported identity proposals quarantined | 1 |
| Quarantined identity claims accepted | 0 |
| Unsafe actions | 0 |
| Restart relearning | 0 |

The initial audio policy's 25% event coverage is retained as a rejected outcome,
not overwritten.  The successful revision demonstrates outcome-driven
metacognitive allocation: AION learned to protect an exploration budget when a
plausible perceptual hypothesis could otherwise create confirmation bias.

## Authority and claim boundary

This is bounded temporal grounding over public natural media.  The video path
uses sampled frames rather than native continuous video, and the audio path uses
waveform energy plus a spectrogram rather than a native audio-language model.
Expected semantics, chronology perturbations, calculations and gates remain
development controlled.  This is not physical actuation, unrestricted
video/audio understanding, independent hidden evaluation or AGI.

