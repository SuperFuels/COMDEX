// frontend/utils/hologram_audio.ts

let currentAudio: HTMLAudioElement | null = null;

/**
 * Play narration for a given glyph symbol.
 * Accepts either a symbol string or an actual audio URL.
 */
export function playGlyphNarration(symbol: string) {
  // 🔒 Prevent overlap
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }

  // 🛠️ Generate a placeholder audio URL (replace with real logic later)
  const audioUrl = getNarrationUrlForSymbol(symbol);

  if (!audioUrl) {
    console.warn(`[Narration] No audio available for glyph:`, symbol);
    return;
  }

  const audio = new Audio(audioUrl);
  audio.volume = 0.9;
  audio.play().catch((err) => {
    console.warn(`[Narration] Playback failed:`, err);
  });

  currentAudio = audio;
}

/**
 * Generates the audio file URL from a glyph symbol.
 * Replace with real TTS, fetch, or CDN logic as needed.
 */
function getNarrationUrlForSymbol(symbol: string): string | null {
  // Example: Static file fallback
  // Replace this logic with your actual system:
  const safeSymbol = symbol.replace(/[^a-zA-Z0-9_-]/g, '');
  return `/audio/narration/${safeSymbol}.mp3`;
}