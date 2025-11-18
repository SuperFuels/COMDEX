// src/lib/kg_emit.ts
// TS wrapper around the UMD global loaded from /public/js/kg_emit.js

type KgEmit = {
  emitTextToKG: (args: any) => Promise<any>;
  emitTranscriptPosted?: (args: any) => Promise<any>;
  emitVoiceToKG: (args: any) => Promise<any>;
  emitPttSession: (args: any) => Promise<any>;
  emitFloorLock?: (args: any) => Promise<any>;
  emitCallState?: (args: any) => Promise<any>;
  emitFileEvent?: (args: any) => Promise<any>;
};

function getAPI(): KgEmit {
  const g = typeof window !== "undefined" ? (window as any).KGEmit : null;
  if (!g) {
    throw new Error(
      'KGEmit UMD script not loaded. Ensure <script src="/js/kg_emit.js"></script> is in index.html.'
    );
  }
  return g as KgEmit;
}

export function emitTextToKG(args: any) {
  return getAPI().emitTextToKG(args);
}

export function emitTranscriptPosted(args: any) {
  const api = getAPI();
  if (!api.emitTranscriptPosted) {
    return Promise.reject(
      new Error("emitTranscriptPosted not available in KGEmit")
    );
  }
  return api.emitTranscriptPosted(args);
}

export function emitVoiceToKG(args: any) {
  return getAPI().emitVoiceToKG(args);
}

export function emitPttSession(args: any) {
  return getAPI().emitPttSession(args);
}

export function emitFloorLock(args: any) {
  const api = getAPI();
  if (!api.emitFloorLock) {
    return Promise.reject(
      new Error("emitFloorLock not available in KGEmit")
    );
  }
  return api.emitFloorLock(args);
}

export function emitCallState(args: any) {
  const api = getAPI();
  if (!api.emitCallState) {
    return Promise.reject(
      new Error("emitCallState not available in KGEmit")
    );
  }
  return api.emitCallState(args);
}

export function emitFileEvent(args: any) {
  const api = getAPI();
  if (!api.emitFileEvent) {
    return Promise.reject(
      new Error("emitFileEvent not available in KGEmit")
    );
  }
  return api.emitFileEvent(args);
}