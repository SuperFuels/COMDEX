// @/utils/callTypes.ts

export type CallId = string;

export type VoiceOffer  = { voice_offer:  { sdp: string; call_id: CallId } };
export type VoiceAnswer = { voice_answer: { sdp: string; call_id: CallId } };
export type IceCapsule  = { ice: { candidate: RTCIceCandidateInit; call_id: CallId } };

// New capsules
export type VoiceCancel = { voice_cancel: { call_id: CallId } };  // caller cancels before answer
export type VoiceReject = { voice_reject: { call_id: CallId } };  // callee declines
export type VoiceEnd    = { voice_end:    { call_id: CallId } };  // either side ends after connect

// Convenience “any-of” shape (useful for narrowing)
export type VoiceCaps = {
  voice_offer?:  { sdp: string; call_id: CallId };
  voice_answer?: { sdp: string; call_id: CallId };
  ice?:          { candidate: RTCIceCandidateInit; call_id: CallId };
  voice_cancel?: { call_id: CallId };
  voice_reject?: { call_id: CallId };
  voice_end?:    { call_id: CallId };
};

// Union of all possible signaling capsules
export type SignalCapsule =
  | VoiceOffer
  | VoiceAnswer
  | IceCapsule
  | VoiceCancel
  | VoiceReject
  | VoiceEnd;