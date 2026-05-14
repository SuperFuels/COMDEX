// src/utils/webrtc.ts
export const DEFAULT_ICE: RTCIceServer[] = [
  { urls: ["stun:stun.l.google.com:19302"] },
  { urls: ["stun:global.stun.twilio.com:3478"] },
];

type Handlers = {
  onLocalDescription?: (sdp: RTCSessionDescriptionInit) => void;
  onLocalIce?: (candidate: RTCIceCandidateInit) => void;
  onRemoteTrack?: (ms: MediaStream) => void;
};

export async function makePeer(
  role: "caller" | "callee",
  handlers: Handlers,
  rtcCfg?: RTCConfiguration
): Promise<RTCPeerConnection> {
  const pc = new RTCPeerConnection({
    iceServers:
      rtcCfg?.iceServers && rtcCfg.iceServers.length ? rtcCfg.iceServers : DEFAULT_ICE,
    iceTransportPolicy: rtcCfg?.iceTransportPolicy || "all",
  });

  pc.onicecandidate = (e) => {
    if (e.candidate && handlers.onLocalIce) handlers.onLocalIce(e.candidate.toJSON());
  };

  pc.ontrack = (ev) => {
    const ms = ev.streams?.[0] || new MediaStream([ev.track]);
    handlers.onRemoteTrack?.(ms);
  };

  // helper so callers can trigger offer/answer emission
  (pc as any)._emitLocalDescription = async (kind: "offer" | "answer") => {
    const desc =
      kind === "offer"
        ? await pc.createOffer({ offerToReceiveAudio: true, offerToReceiveVideo: false })
        : await pc.createAnswer();
    await pc.setLocalDescription(desc);
    handlers.onLocalDescription?.(desc);
  };

  return pc;
}

// src/utils/webrtc.ts
export async function fetchIceFromServer(base: string) {
  try {
    const r = await fetch(`${base}/api/rtc/ice`);
    if (!r.ok) throw new Error(String(r.status));
    const j = await r.json();
    const list = j?.iceServers;
    return (Array.isArray(list) && list.length) ? list : DEFAULT_ICE;
  } catch {
    return DEFAULT_ICE;
  }
}