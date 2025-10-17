# ──────────────────────────────────────────────────────────────
#  Tessaris • Voice Interface (AION v3)
#  ElevenLabs → Google Cloud Storage voice output bridge
#  Handles AION speech synthesis & public audio publishing.
# ──────────────────────────────────────────────────────────────

import os
import requests
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import storage

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# ──────────────────────────────────────────────────────────────
#  Environment Setup
# ──────────────────────────────────────────────────────────────
# Use .env first, fallback to .env.local if needed
root_path = Path(__file__).resolve().parents[3]
env_local = root_path / ".env.local"
if env_local.exists():
    load_dotenv(dotenv_path=env_local)
else:
    load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "ZF6FPAbjXT4488VcRRnw")
BUCKET_NAME = os.getenv("ELEVENLABS_BUCKET", "tessaris-voice-outputs")

# ──────────────────────────────────────────────────────────────
#  Voice Interface Class
# ──────────────────────────────────────────────────────────────
class VoiceInterface:
    def __init__(self):
        self.enabled = bool(ELEVENLABS_API_KEY)
        self.voice_id = VOICE_ID
        self.bucket = BUCKET_NAME

        if self.enabled:
            print(f"✅ ElevenLabs voice interface ready (Voice ID: {self.voice_id})")
        else:
            print("⚠️ ElevenLabs API key not set — voice output disabled.")

    # ──────────────────────────────────────────────
    def speak(self, text: str) -> str:
        """
        Convert AION’s generated text into speech via ElevenLabs API.
        Returns the public URL of the generated audio if upload succeeds.
        """
        if not self.enabled:
            print(f"🔇 (Voice disabled) — AION says: {text}")
            return None

        print(f"🗣️ Synthesizing AION speech → {text[:60]}{'...' if len(text) > 60 else ''}")
        try:
            # ElevenLabs synthesis request
            resp = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.45,
                        "similarity_boost": 0.8,
                    },
                },
                timeout=30,
            )

            if resp.status_code != 200:
                print(f"❌ Voice generation failed: {resp.status_code} {resp.text}")
                return None

            local_path = f"backend/modules/skills/voice_output_{os.getpid()}.mp3"
            with open(local_path, "wb") as f:
                f.write(resp.content)
            print(f"🔊 Voice generated locally at: {local_path}")

            return self.upload_to_gcs(local_path)

        except Exception as e:
            print(f"❌ Voice synthesis error: {e}")
            return None

    # ──────────────────────────────────────────────
    def upload_to_gcs(self, local_path: str) -> str:
        """
        Uploads synthesized speech to Google Cloud Storage and returns its public URL.
        """
        try:
            client = storage.Client()
            bucket = client.bucket(self.bucket)
            filename = os.path.basename(local_path)
            blob = bucket.blob(filename)
            blob.upload_from_filename(local_path)

            url = f"https://storage.googleapis.com/{self.bucket}/{filename}"
            print(f"🌐 Voice published at: {url}")
            return url

        except Exception as e:
            print(f"❌ Failed to upload to GCS: {e}")
            return None