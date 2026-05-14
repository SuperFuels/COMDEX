const API_KEY = process.env.NEXT_PUBLIC_ELEVENLABS_API_KEY || "";
const VOICE_ID = "EXAVITQu4vr4xnSDxMaL"; // Default voice (can be replaced)

let audioContext: AudioContext | null = null;

/**
 * Play TTS narration for a glyph or message using ElevenLabs API.
 */
export async function playGlyphNarration(
  text: string,
  options: {
    voice?: string;
    language?: string;
  } = {}
) {
  if (!API_KEY) {
    console.warn("🔇 ElevenLabs API key not set");
    return;
  }

  try {
    if (!audioContext) {
      audioContext = new AudioContext();
    }

    const url = `https://api.elevenlabs.io/v1/text-to-speech/${options.voice || VOICE_ID}`;
    const body = {
      text,
      model_id: "eleven_monolingual_v1",
      voice_settings: {
        stability: 0.4,
        similarity_boost: 0.75,
      },
    };

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`TTS failed: ${response.statusText}`);
    }

    const arrayBuffer = await response.arrayBuffer();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    source.start(0);
  } catch (error) {
    console.error("🔇 Error playing TTS:", error);
  }
}

/**
 * Preloads available ElevenLabs voices (optional).
 */
export async function preloadVoices(): Promise<any[]> {
  if (!API_KEY) {
    console.warn("ElevenLabs API key not set.");
    return [];
  }

  try {
    const response = await fetch("https://api.elevenlabs.io/v1/voices", {
      headers: {
        "xi-api-key": API_KEY,
      },
    });

    if (!response.ok) {
      throw new Error("Failed to fetch voices");
    }

    const data = await response.json();
    return data.voices || [];
  } catch (error) {
    console.error("Error preloading voices:", error);
    return [];
  }
}

/**
 * Handle glyph narration playback from a GHX glyph object.
 */
export function speakFromGlyph(glyph: {
  symbol: string;
  narration?: {
    text_to_speak: string;
    voice?: string;
    language?: string;
  };
}) {
  const narration = glyph.narration;
  if (narration?.text_to_speak) {
    playGlyphNarration(narration.text_to_speak, {
      voice: narration.voice,
      language: narration.language,
    });
  } else {
    playGlyphNarration(`Glyph ${glyph.symbol}`);
  }
}