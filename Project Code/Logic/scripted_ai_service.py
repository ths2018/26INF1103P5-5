from Logic.ai_service import AIService


class ScriptedAIService(AIService):
    """Test implementation: returns hard-coded replies, never calls an API."""

    def __init__(self, replies, relevant=True):
        self._replies = list(replies)
        self._relevant = relevant
        self.received = []  # everything the app sent, for assertions

    def create_chat(self, case):
        return object()

    def ask(self, chat, text):
        self.received.append(text)
        return self._replies.pop(0) if self._replies else None

    def is_relevant(self, text, case):
        return self._relevant
