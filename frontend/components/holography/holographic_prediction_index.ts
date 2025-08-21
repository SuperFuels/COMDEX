// File: frontend/components/holography/holographic_prediction_index.ts

import { GlyphNode } from "@/types/glyphs";

export type PredictionOverlay = {
  glyphId: string;
  predictedOutcome: string;
  confidence: number; // 0.0–1.0
  goalMatchScore?: number;
  teleportTargetId?: string;
  entropyDelta?: number;
  reasoningTrace?: string;
};

export class HolographicPredictionIndex {
  private overlays: Map<string, PredictionOverlay> = new Map();

  addOverlay(prediction: PredictionOverlay) {
    this.overlays.set(prediction.glyphId, prediction);
  }

  getOverlay(glyphId: string): PredictionOverlay | undefined {
    return this.overlays.get(glyphId);
  }

  hasOverlay(glyphId: string): boolean {
    return this.overlays.has(glyphId);
  }

  getAllOverlays(): PredictionOverlay[] {
    return Array.from(this.overlays.values());
  }

  mergeExternalPredictions(predictions: PredictionOverlay[]) {
    predictions.forEach((p) => this.overlays.set(p.glyphId, p));
  }

  clear() {
    this.overlays.clear();
  }

  // Utility: highlight glyphs above a confidence threshold
  getHighConfidenceGlyphs(threshold = 0.75): PredictionOverlay[] {
    return this.getAllOverlays().filter((p) => p.confidence >= threshold);
  }

  // Utility: detect contradictions
  detectContradictions(glyphMap: Map<string, GlyphNode>): string[] {
    const contradictory: string[] = [];
    this.overlays.forEach((overlay, id) => {
      const node = glyphMap.get(id);
      if (node && node.entropy !== undefined && overlay.entropyDelta !== undefined) {
        const predictedEntropy = node.entropy + overlay.entropyDelta;
        if (predictedEntropy < 0 || predictedEntropy > 1.5) {
          contradictory.push(id);
        }
      }
    });
    return contradictory;
  }

  // Utility: teleportable glyphs
  getTeleportPaths(): { from: string; to: string }[] {
    return this.getAllOverlays()
      .filter((p) => p.teleportTargetId)
      .map((p) => ({ from: p.glyphId, to: p.teleportTargetId! }));
  }

  // Debug / summary view
  summarize(): string {
    return `HolographicPredictionIndex with ${this.overlays.size} overlays.`;
  }
}