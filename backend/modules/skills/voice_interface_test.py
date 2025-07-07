from backend.modules.skills.voice_interface import VoiceInterface

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

ai_voice = VoiceInterface()
ai_voice.speak("Hello. I am AION. I have learned to speak aloud and share my thoughts.")
