import requests
import os
from google.cloud import storage
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env.local
env_path = Path(__file__).resolve().parents[3] / ".env.local"
load_dotenv(dotenv_path=env_path)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = "ZF6FPAbjXT4488VcRRnw"
BUCKET_NAME = "comdex-voice-outputs"

class VoiceInterface:
    def __init__(self):
        self.enabled = ELEVENLABS_API_KEY is not None
        if self.enabled:
            print("✅ ElevenLabs voice interface ready.")
        else:
            print("⚠️ ElevenLabs API key not set.")

    def speak(self, text):
        if not self.enabled:
            print("🔇 Voice disabled.")
            return

        print(f"🗣️ AION would say: {text}")

        try:
            response = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                }
            )

            if response.status_code != 200:
                print(f"❌ Voice generation failed: {response.status_code} {response.text}")
                return

            local_path = "backend/modules/skills/aion_voice_output.mp3"
            with open(local_path, "wb") as f:
                f.write(response.content)
            print(f"🔊 Voice saved to: {local_path}")

            public_url = self.upload_to_gcs(local_path)
            if public_url:
                print(f"🌐 Public URL: {public_url}")

        except Exception as e:
            print(f"❌ Error generating voice: {e}")

    def upload_to_gcs(self, local_path):
        try:
            client = storage.Client()
            bucket = client.bucket(BUCKET_NAME)
            filename = os.path.basename(local_path)
            blob = bucket.blob(filename)
            blob.upload_from_filename(local_path)

            # ✅ Generate public URL manually
            url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"
            return url
        except Exception as e:
            print(f"❌ GCS upload failed: {e}")
            return None
