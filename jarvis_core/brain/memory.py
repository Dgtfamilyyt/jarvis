class Memory:
    def __init__(self):
        self._history = []

    def add(self, role: str, text: str):
        self._history.append({"role": role, "text": text})

    def recent(self, n: int = 10):
        return self._history[-n:]
