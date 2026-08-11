# Tessaris Marketing Creative Intelligence Lab

Date: 10 August 2026

## Purpose

Tessaris now owns the creative campaign contract above replaceable image and
video models. The contract covers brand-grounded direction, storyboards,
platform renditions, clipping instructions, experiments, approval and evidence.

## Implemented

- Provider-neutral image, original-video, clip and carousel planning.
- Platform profiles for Instagram, Facebook, TikTok, YouTube Shorts and LinkedIn.
- Correct portrait/feed output contracts, subtitle requirements and safe zones.
- Five-scene storyboard and shot-list generation.
- Replaceable provider contracts for OpenAI Sora, Gemini Veo, Runway and Luma.
- Optional provider registry for fal and native Tessaris post-production.
- Single-variable A/B challengers for hook, opening visual and call to action.
- Frozen minimum sample, improvement threshold, complaint and truthfulness guards.
- Winner-candidate selection without automatic traffic, spend or publishing changes.
- A Creative Intelligence Lab embedded in the unified Marketing workspace.

## API

- `GET /api/aion/marketing/creative/capabilities`
- `GET /api/aion/marketing/creative/platforms`
- `POST /api/aion/marketing/creative/plan`
- `POST /api/aion/marketing/creative/experiment/evaluate`

## Governance

Render jobs are plans until approved. Experiment winners are candidates until
approved. No endpoint in this increment can publish, spend money, alter campaign
traffic or promote an unsafe creative. Generated claims must be supported by
business evidence.

## Provider decision

Use direct Gemini and OpenAI routes first because they are already part of the
Tessaris provider layer. Runway, Luma and fal remain optional specialist engines.
Higgsfield and OpenArt are useful product-design references, but are not required
as core dependencies. This prevents the Marketing operating system from becoming
locked to a wrapper whose models, pricing or API availability can change.

## Honest remaining boundary

Paid live Sora and Veo submission is implemented but was deliberately not
charged during verification. The desktop now automatically monitors submitted
provider jobs, so a completed asset is downloaded without relying on a person to
press the status button. Provider-native webhook callbacks remain optional future
optimisation; they are not required for unattended completion. Publishing and
advertising connectors remain separate, approval-gated increments.

## Paid rendering and local post-production increment

The next production layer was added later on 10 August 2026:

- Persistent Sora and Veo video jobs stored per business workspace.
- Exact hash approval binding the provider, model, prompt, duration, resolution
  and reference asset.
- A required positive euro cost ceiling and explicit paid-generation authority.
- Separate prepare, approve, submit and poll operations.
- Permanent download of completed provider footage into the Tessaris workspace,
  including byte count and SHA-256 evidence.
- Native local timeline projects containing ordered source clips and trim points.
- FFmpeg 7.1 platform export to 1080x1920 or the relevant platform dimensions.
- Audio preservation or generated silence when the source has no audio.
- Final MP4 fast-start packaging, thumbnail creation and output hashing.
- A native macOS video picker exposed through a minimal Electron IPC boundary.

## Visual editor completion increment

The local editor now also provides:

- multi-select video import and a visual, drag-and-drop ordered clip timeline;
- independent in and out points for every clip;
- cut, fade, dissolve, wipe and slide transitions with bounded duration;
- editable timed subtitle entries using a simple `start-end|text` track;
- timed campaign text overlays with safe top, centre and bottom positions;
- local logo or watermark overlay;
- background-music import, looping, volume control and mixing with source audio;
- OpenAI reference-image selection with a one-image limit;
- Gemini reference-image selection with a three-image limit and correct inline
  image payloads; and
- a background render monitor that polls submitted Sora and Veo jobs and stores
  completed footage locally with provenance and hashes.

The physical verification exported a real two-clip vertical H.264/AAC MP4 with a
fade transition, two burned subtitle cues, a timed text overlay, logo and mixed
music. No paid provider generation was invoked.

## Premium production and publication increment

The editor was subsequently extended beyond deterministic cutting:

- per-clip static, slow zoom-in, slow zoom-out, left-pan and right-pan motion;
- bounded motion intensity with source-duration-aware frame calculations;
- none, fade and slide-up title animation;
- clean, bold-commercial and cinematic brand treatments;
- an independent voice-over track with start time and gain controls;
- direct local microphone narration recording into the business workspace;
- automatic side-chain music ducking under narration;
- music fade-in and fade-out;
- social and broadcast loudness-mastering presets;
- a hash-bound publication package containing the exact asset, caption, CTA,
  channel, mode, schedule and budget;
- connector-readiness reporting for organic channels, Meta Ads and Google Ads;
- real outcome evidence for impressions, clicks, qualified actions, conversions,
  spend, revenue, complaints and unsafe claims; and
- calculated CTR, qualified-action rate, conversion rate, cost per qualified
  action and ROAS.

External publication remains fail-closed. A publication package can be prepared
and exactly approved, but the present service exposes no execution endpoint.
Missing business credentials are shown explicitly. This prevents an editor
action from silently publishing content or creating advertising spend.

The premium physical proof produced a 5.4-second 1080x1920 H.264/AAC master with
two motion-treated clips, dissolve, animated title, subtitles, logo, music,
separate narration, automatic ducking and social loudness mastering. Its SHA-256
digest is `816264199101da6915bb50dd192b963bc174e2ba755ff30766171aa4f85d5e4b`.

Paid execution is not automatic. A prepared job without the explicit boolean
authority, exact approval hash and maximum euro ceiling fails closed. The test
cycle deliberately prepared and approved a dummy job but did not submit it to a
provider, so no generation charge was incurred.

### Additional API

- `GET /api/aion/marketing/creative/{workspace_id}/renders`
- `POST /api/aion/marketing/creative/{workspace_id}/renders`
- `POST /api/aion/marketing/creative/{workspace_id}/renders/{job_id}/approve`
- `POST /api/aion/marketing/creative/{workspace_id}/renders/{job_id}/submit`
- `POST /api/aion/marketing/creative/{workspace_id}/renders/{job_id}/poll`
- `POST /api/aion/marketing/creative/{workspace_id}/timelines`
- `POST /api/aion/marketing/creative/{workspace_id}/timelines/{timeline_id}/export`
- `POST /api/aion/marketing/creative/{workspace_id}/voiceovers`
- `POST /api/aion/marketing/creative/{workspace_id}/publications`
- `GET /api/aion/marketing/creative/{workspace_id}/publications/{package_id}`
- `POST /api/aion/marketing/creative/{workspace_id}/publications/{package_id}/approve`
- `POST /api/aion/marketing/creative/{workspace_id}/publications/{package_id}/outcomes`
