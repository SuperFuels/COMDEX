export type CallId = string;

export type VoiceOffer = { voice_offer: { sdp: string; call_id: CallId } };
export type VoiceAnswer = { voice_answer: { sdp: string; call_id: CallId } };
export type IceCapsule = { ice: { candidate: any; call_id: CallId } };

export type SignalCapsule = VoiceOffer | VoiceAnswer | IceCapsule;