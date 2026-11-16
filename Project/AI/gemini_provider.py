
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

CHAT_MODEL = "gemini-3.5-flash-lite"
CHECK_MODEL = "gemini-3.5-flash"


class GeminiProvider:

    def __init__(self):
        """Initialises the Gemini API client."""

        api_key = os.getenv("GENAI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GENAI_API_KEY environment variable is not set."
            )

        self.client = genai.Client(api_key=api_key)

    def create_chat(self, system_instruction, history=None):
        """Creates a Gemini chat with the supplied history."""

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json"
        )

        return self.client.chats.create(
            model=CHAT_MODEL,
            config=config,
            history=history or []
        )

    def send_message(self, chat, user_input):
        """Sends a message to the active Gemini chat."""

        response = chat.send_message(message=user_input)

        return getattr(response, "text", None)

    def generate_text(self, prompt):
        """Generates a standalone response for relevance checking."""

        response = self.client.models.generate_content(
            model=CHECK_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                automatic_function_calling=(
                    types.AutomaticFunctionCallingConfig(
                        disable=True
                    )
                )
            )
        )

        return getattr(response, "text", None)
