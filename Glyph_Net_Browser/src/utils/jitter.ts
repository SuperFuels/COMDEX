type Frame = { seq: number; ts: number; data: Uint8Array };

export class JitterBuffer {
  private buf = new Map<number, Frame>();
  private expected = 0;
  private holdMs = 100;
  constructor(holdMs = 100) { this.holdMs = holdMs; }

  push(f: Frame) {
    this.buf.set(f.seq, f);
    if (this.expected === 0) this.expected = f.seq;
  }

  // Call at ~50–100 Hz; returns frames in order, or null
  pull(nowMs = Date.now()): Frame | null {
    const f = this.buf.get(this.expected);
    if (!f) return null;

    // hold a little so mild reordering can be absorbed
    if (nowMs - f.ts < this.holdMs) return null;

    this.buf.delete(this.expected++);
    return f;
  }
}