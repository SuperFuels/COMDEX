// Glyph_Net_Browser/src/lib/audio/jitter.ts
export class VoiceJitterBuffer {
  private ctx: AudioContext;
  private nextSeq = -1;
  private queue: Map<number, ArrayBuffer> = new Map();
  private playing = false;
  private gain: GainNode;

  constructor(ctx?: AudioContext) {
    this.ctx = ctx ?? new (window.AudioContext || (window as any).webkitAudioContext)();
    this.gain = this.ctx.createGain();
    this.gain.connect(this.ctx.destination);
  }

  setVolume(v: number) {
    this.gain.gain.value = Math.max(0, Math.min(1, v));
  }

  async push(seq: number, mime: string, b64: string) {
    const bin = atob(b64);
    const buf = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
    this.queue.set(seq, buf.buffer);
    if (!this.playing) this.drain();
  }

  private async drain() {
    this.playing = true;
    try {
      if (this.nextSeq < 0) {
        // bootstrap to smallest seq available
        if (this.queue.size === 0) return;
        this.nextSeq = Math.min(...this.queue.keys());
      }
      while (true) {
        const data = this.queue.get(this.nextSeq);
        if (!data) {
          // small wait for late frames
          await new Promise(r => setTimeout(r, 30));
          if (!this.queue.get(this.nextSeq)) break;
          continue;
        }
        this.queue.delete(this.nextSeq);
        const audioBuf = await this.ctx.decodeAudioData(data.slice(0));
        const src = this.ctx.createBufferSource();
        src.buffer = audioBuf;
        src.connect(this.gain);
        // start ASAP; no precise wall-clock here—low latency > sample-perfect sync
        src.start();
        this.nextSeq++;
        // small pacing delay so decode/start don’t stampede
        await new Promise(r => setTimeout(r, 5));
      }
    } finally {
      this.playing = false;
    }
  }
}
