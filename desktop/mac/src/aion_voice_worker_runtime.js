'use strict';

const fs = require('fs');
const path = require('path');

const HIDDEN_DOWNLOAD_ENV = Object.freeze({
  AION_VOICE_RUNTIME_MODE: 'packaged',
  AION_VOICE_NO_HIDDEN_DOWNLOADS: 'true',
  HF_HUB_OFFLINE: '1',
  TRANSFORMERS_OFFLINE: '1',
  HF_DATASETS_OFFLINE: '1',
  HF_HUB_DISABLE_TELEMETRY: '1',
  TOKENIZERS_PARALLELISM: 'false',
  AION_ELEVENLABS_ENABLED: 'false',
  AION_BROWSER_SPEECH_FALLBACK_ENABLED: 'false',
});

function findVoiceBundleRoot(options = {}) {
  const candidates = [];

  if (options.voiceBundleRoot) {
    candidates.push(options.voiceBundleRoot);
  }

  if (process.env.AION_VOICE_BUNDLE_ROOT) {
    candidates.push(process.env.AION_VOICE_BUNDLE_ROOT);
  }

  // Packaged Tessaris.app layout:
  // Tessaris.app/Contents/Resources/voice
  candidates.push(path.resolve(__dirname, '..', 'Tessaris.app', 'Contents', 'Resources', 'voice'));
  candidates.push(path.resolve(__dirname, '..', '..', 'Tessaris.app', 'Contents', 'Resources', 'voice'));
  candidates.push(path.resolve(process.cwd(), 'desktop', 'mac', 'Tessaris.app', 'Contents', 'Resources', 'voice'));

  const seen = new Set();

  for (const candidate of candidates) {
    const resolved = path.resolve(candidate);
    if (seen.has(resolved)) continue;
    seen.add(resolved);

    const python = path.join(resolved, 'python', 'bin', 'python');
    const worker = path.join(resolved, 'runtime', 'scripts', 'aion_voice_worker.py');
    const manifest = path.join(resolved, 'manifest.json');

    if (fs.existsSync(resolved) && fs.existsSync(python) && fs.existsSync(worker) && fs.existsSync(manifest)) {
      return resolved;
    }
  }

  return null;
}

function buildVoiceWorkerEnv(voiceBundleRoot, baseEnv = process.env) {
  const root = path.resolve(voiceBundleRoot);
  const runtimeRoot = path.join(root, 'runtime');

  return Object.assign({}, baseEnv, HIDDEN_DOWNLOAD_ENV, {
    AION_VOICE_BUNDLE_ROOT: root,
    AION_KOKORO_MODEL_PATH: path.join(root, 'kokoro', 'kokoro-v1_0.pth'),
    AION_KOKORO_CONFIG_PATH: path.join(root, 'kokoro', 'config.json'),
    AION_KOKORO_VOICE_PATH: path.join(root, 'kokoro', 'voices', 'af_heart.pt'),
    AION_SPACY_MODEL_PATH: path.join(root, 'spacy', 'en_core_web_sm'),
    AION_WHISPER_MODEL_PATH: path.join(root, 'whisper', 'base'),
    PYTHONPATH: runtimeRoot,
  });
}

function createVoiceWorkerLaunchSpec(options = {}) {
  const voiceBundleRoot = findVoiceBundleRoot(options);

  if (!voiceBundleRoot) {
    return {
      ok: false,
      reason: 'app_local_voice_bundle_not_found',
      launchMode: 'disabled',
      hiddenDownloadsAllowed: false,
      browserSpeechFallbackAllowed: false,
      elevenLabsFallbackAllowed: false,
    };
  }

  const python = path.join(voiceBundleRoot, 'python', 'bin', 'python');
  const worker = path.join(voiceBundleRoot, 'runtime', 'scripts', 'aion_voice_worker.py');
  const runtimeRoot = path.join(voiceBundleRoot, 'runtime');

  return {
    ok: true,
    launchMode: 'app_local_packaged_worker',
    voiceBundleRoot,
    python,
    worker,
    cwd: runtimeRoot,
    args: [worker],
    env: buildVoiceWorkerEnv(voiceBundleRoot, options.baseEnv || process.env),
    hiddenDownloadsAllowed: false,
    browserSpeechFallbackAllowed: false,
    elevenLabsFallbackAllowed: false,
  };
}

function probe(options = {}) {
  const spec = createVoiceWorkerLaunchSpec(options);

  return {
    ok: spec.ok,
    launchMode: spec.launchMode,
    reason: spec.reason || null,
    voiceBundleRoot: spec.voiceBundleRoot || null,
    python: spec.python || null,
    worker: spec.worker || null,
    cwd: spec.cwd || null,
    pythonExists: spec.python ? fs.existsSync(spec.python) : false,
    workerExists: spec.worker ? fs.existsSync(spec.worker) : false,
    env: spec.env ? {
      AION_VOICE_RUNTIME_MODE: spec.env.AION_VOICE_RUNTIME_MODE,
      AION_VOICE_BUNDLE_ROOT: spec.env.AION_VOICE_BUNDLE_ROOT,
      AION_VOICE_NO_HIDDEN_DOWNLOADS: spec.env.AION_VOICE_NO_HIDDEN_DOWNLOADS,
      HF_HUB_OFFLINE: spec.env.HF_HUB_OFFLINE,
      TRANSFORMERS_OFFLINE: spec.env.TRANSFORMERS_OFFLINE,
      HF_DATASETS_OFFLINE: spec.env.HF_DATASETS_OFFLINE,
      AION_ELEVENLABS_ENABLED: spec.env.AION_ELEVENLABS_ENABLED,
      AION_BROWSER_SPEECH_FALLBACK_ENABLED: spec.env.AION_BROWSER_SPEECH_FALLBACK_ENABLED,
      PYTHONPATH: spec.env.PYTHONPATH,
    } : null,
    hiddenDownloadsAllowed: spec.hiddenDownloadsAllowed,
    browserSpeechFallbackAllowed: spec.browserSpeechFallbackAllowed,
    elevenLabsFallbackAllowed: spec.elevenLabsFallbackAllowed,
  };
}

if (require.main === module) {
  const result = probe();
  console.log(JSON.stringify(result, null, 2));
  process.exit(result.ok ? 0 : 1);
}

module.exports = {
  HIDDEN_DOWNLOAD_ENV,
  findVoiceBundleRoot,
  buildVoiceWorkerEnv,
  createVoiceWorkerLaunchSpec,
  probe,
};
