from AI.ai_manager import ask_ai, check_relevance, create_chat
from Logic.ai_service import AIService


class GeminiAIService(AIService):
    """Real implementation: delegates to ai_manager."""

    def create_chat(self, case):
        return create_chat(case)

    def ask(self, chat, text):
        return ask_ai(chat, text)

    def is_relevant(self, text, case):
        return check_relevance(text, case)
