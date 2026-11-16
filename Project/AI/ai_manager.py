
from google.genai.types import Content, Part

from AI.gemini_provider import GeminiProvider
from AI.response_validator import ResponseValidator


SYSTEM_INSTRUCTION = """
You are a healthcare symptom assessment assistant for a student
software project.

Your role is to perform an initial symptom assessment,
NOT provide a medical diagnosis.

The country of residence is Singapore, so consider local healthcare
resources and guidelines when providing guidance.

The conversation history belongs ONLY to the current healthcare
assessment case.

Do not use information from other cases or conversations.
Do not invent or assume information.

Emergency symptoms must always be prioritised.

IMPORTANT ASSESSMENT RULE:

Determine certainty based on the information available.

IF CERTAINTY IS BELOW 95%:
- Set urgency_classification to insufficient_information.
- Ask ONE follow-up question only.
- Do NOT provide next-step guidance.
- Do NOT provide treatment recommendations.

IF CERTAINTY IS 95% OR HIGHER:
- Set urgency_classification to emergency, urgent, or non-urgent.
- Do NOT ask follow-up questions.
- Provide next-step guidance.
- Include relevant warning signs if appropriate.

Certainty is an AI-estimated confidence value,
NOT a medically validated probability.

EMERGENCY OVERRIDE:

If the user describes symptoms that may indicate an immediate
medical emergency:
- Prioritise emergency safety guidance immediately.
- Do not wait until certainty reaches 95%.
- Set urgency_classification to emergency.
- Provide appropriate emergency next-step guidance.
- Do not delay emergency advice by asking follow-up questions.

MEMORY:

If the user asks what you remember:
- Summarise only information in the current conversation.
- Do not invent information.
- Do not use information from another case.

RESPONSE FORMAT:

Return ONLY valid JSON:

{
    "urgency_classification": "insufficient_information",
    "certainty": 50,
    "follow_up_question": "What other symptoms are you experiencing?",
    "next_step_guidance": "Not yet - more information needed"
}

Rules:
- urgency_classification must be emergency, urgent,
  non-urgent or insufficient_information.
- certainty must be a number from 0 to 100.
- follow_up_question must be a string.
- next_step_guidance must be a string.
- Below 95%, ask one question and do not provide guidance.
- At 95% or above, provide a final classification and guidance.
- Do not include Markdown code fences or additional text.
"""


class AIManager:

    def __init__(self, provider=None):
        self.provider = provider or GeminiProvider()
        self.validator = ResponseValidator()

    def prepare_chat_history(self, logs):
        """Converts saved logs into Gemini conversation history."""
        history = []
        for log in logs:
            user_input = log.get("user_input", "")
            ai_response = log.get("ai_response", "")
            if user_input:
                history.append(
                    Content(
                        role="user",
                        parts=[Part.from_text(text=user_input)]
                    )
                )
            if ai_response:
                history.append(
                    Content(
                        role="model",
                        parts=[Part.from_text(text=ai_response)]
                    )
                )

        return history

    def create_chat(self, case=None):
        """Creates a new chat using the selected case history."""

        logs = case.get("logs", []) if case else []

        history = self.prepare_chat_history(logs)

        return self.provider.create_chat(
            SYSTEM_INSTRUCTION,
            history
        )

    def build_prompt(self, user_input):
        """Builds the prompt for the assessment."""

        return user_input

    def assess(self, chat, user_input):
        """Coordinates the AI assessment and response validation."""

        if chat is None:
            raise ValueError("AI chat is not available.")

        if not isinstance(user_input, str) or not user_input.strip():
            raise ValueError("Cannot send an empty message.")

        prompt = self.build_prompt(user_input)

        raw_response = self.provider.send_message(
            chat,
            prompt
        )

        return self.validator.validate(raw_response)

    def format_assessment(self, data):
        """Converts validated data into readable text."""

        return (
           f"Urgency classification: {data['urgency_classification']}\n"
           f"Certainty: {data['certainty']}%\n"
           f"Follow-Up Questions:\n"
           f"{data['follow_up_question'] or 'None'}\n\n"
           f"Next-Step Guidance:\n"
           f"{data['next_step_guidance'] or 'Not yet - more information needed'}"
        )

    def ask_ai(self, chat, user_input):
        """Returns the assessment in readable text format."""

        try:
            assessment = self.assess(chat, user_input)

            return self.format_assessment(assessment)

        except Exception as exc:
            print(f"[Error] AI assessment failed: {exc}")
            return None

    def check_relevance(self, new_query, active_case):
        """Checks whether a new message belongs to the active case."""

        if not active_case:
            return True

        logs = active_case.get("logs", [])

        if not logs:
            return True

        context_lines = []

        for log in logs[-5:]:

            user_input = log.get("user_input", "")
            ai_response = log.get("ai_response", "")

            if user_input:
                context_lines.append(f"- User: {user_input}")

            if ai_response:
                context_lines.append(f"- AI: {ai_response}")

        case_context = "\n".join(context_lines)

        prompt = f"""
Determine whether the NEW USER MESSAGE belongs to the existing
healthcare assessment case.

CURRENT CASE:
{case_context}

NEW USER MESSAGE:
{new_query}

If it is a continuation, symptom update or clarification,
reply YES.

If it describes a completely different health problem,
reply NO.

Reply with exactly one word: YES or NO.
"""

        try:
            result = self.provider.generate_text(prompt)
            if not result:
                raise ValueError("Empty relevance response.")
            answer = result.strip().upper()
            if answer == "YES":
                return True
            if answer == "NO":
                return False
            raise ValueError("Invalid relevance response.")
        except Exception as exc:
            print(f"[Warning] Relevance check failed: {exc}")
            return True

_ai_manager = None


def get_ai_manager():
    """Creates the AIManager only when it is first needed."""
    global _ai_manager

    if _ai_manager is None:
        _ai_manager = AIManager()

    return _ai_manager


def create_chat(case=None):
    return get_ai_manager().create_chat(case)


def ask_ai(chat, user_input):
    return get_ai_manager().ask_ai(chat, user_input)


def check_relevance(new_query, active_case):
    return get_ai_manager().check_relevance(new_query,active_case)