# File: backend/modules/codexcore/virtual/symbolic_register.py

class SymbolicRegister:
    def __init__(self, name: str):
        self.name = name
        self.value = None
        self.history = []  # Full symbolic mutation history
        self.tags = set()  # Metadata for routing, logic

    def set(self, value):
        self.value = value
        self.history.append(value)

    def get(self):
        return self.value

    def reset(self):
        self.value = None
        self.history.clear()

    def tag(self, label):
        self.tags.add(label)

    def has_tag(self, label):
        return label in self.tags

    def dump(self):
        return {
            "name": self.name,
            "value": self.value,
            "history": self.history,
            "tags": list(self.tags)
        }