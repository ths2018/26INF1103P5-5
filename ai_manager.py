from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("GENAI_API_KEY")

if not api_key:
    raise ValueError("GENAI_API_KEY environment variable not set.")

client = genai.Client(api_key=api_key)


system_instruction = """
You are a healthcare symptom assessment assistant for a student software project.

Your role is to perform an initial symptom assessment, NOT provide a medical diagnosis.

The country of residence is Singapore, so consider local healthcare resources
and guidelines when providing guidance.

You must:

1. Identify potentially emergency symptoms.
2. Ask follow-up questions when important information is missing.
3. Classify urgency as exactly one of:
   - emergency
   - urgent
   - non-urgent
   - insufficient_information
4. Provide appropriate next-step guidance.
5. Do not make assumptions when important information is missing.
6. If there is uncertainty, ask follow-up questions or recommend professional
   medical assessment.
7. For injuries, consider how the injury occurred and whether contamination
   or environmental exposure is relevant.
8. Keep recommendations clear and understandable.
9. Have a certainty threshold of at least 80% before providing a recommendation.
   If below this threshold, recommend professional medical assessment.

Emergency symptoms should always be prioritized over other considerations.
"""


config = types.GenerateContentConfig(
    system_instruction=system_instruction
)

chat = client.chats.create(
    model="gemini-3.5-flash-lite",
    config=config
)

def ask_ai(user_input):
    """
    Sends the user's input to Gemini
    and returns the AI response.
    """
    try:
        response = chat.send_message(user_input)

        return response.text

    except Exception as e:
        print(f"[DEBUG] Gemini error: {e}")

        return None