import random

class EmotionEngine:
    """
    Simulates emotional states and fluctuations based on events and input content.
    """

    def __init__(self):
        self.current_emotion = "neutral"
        self.history = []

    def interpret_input(self, text: str) -> str:
        # Naive keyword-based sentiment interpretation
        text_lower = text.lower()
        positive = ["happy", "love", "hope", "excited", "grateful", "fun"]
        negative = ["sad", "hate", "fear", "angry", "pain", "alone"]

        if any(word in text_lower for word in positive):
            return "positive"
        elif any(word in text_lower for word in negative):
            return "negative"
        return "neutral"

    def shift_emotion(self, emotion: str):
        if emotion not in ["positive", "negative", "neutral"]:
            emotion = "neutral"
        self.current_emotion = emotion
        self.history.append({"emotion": emotion})

    def get_emotion(self) -> str:
        return self.current_emotion

    def react_to_event(self, event: str):
        if "failure" in event.lower() or "error" in event.lower():
            self.shift_emotion("negative")
        elif "success" in event.lower() or "reward" in event.lower():
            self.shift_emotion("positive")
        else:
            self.shift_emotion(random.choice(["neutral", "neutral", self.current_emotion]))

    def summarize_emotion_state(self) -> str:
        return f"Emotion: {self.current_emotion} | History Length: {len(self.history)}"
