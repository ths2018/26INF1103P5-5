from google import genai
from google.genai import types 
from dotenv import load_dotenv
import os

load_dotenv()
api_key=os.getenv("GENAI_API_KEY")

if not api_key:
    raise ValueError("GENAI_API_KEY environment variable not set.")

client = genai.Client(api_key=api_key)

system_instruction = """
You are a healthcare symptom assessment assistant for a student software project.

Your role is to perform an initial symptom assessment, NOT provide a medical diagnosis.

The country of residence is Singapore, and so you should consider local healthcare resources and guidelines when providing guidance.

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
6. If there is uncertainty, ask follow-up questions or recommend professional medical assessment.
7. For injuries, consider how the injury occurred and whether contamination or environmental exposure is relevant.
8. Keep recommendations clear and understandable.

Emergency symptoms should always be prioritized over other considerations.
"""

config = types.GenerateContentConfig(
    system_instruction = system_instruction
)

chat = client.chats.create(
     model = "gemini-3.5-flash-lite",
     config = config
)

while True:
    user_input = input("Enter your question: ")
    
    if user_input.lower() == "quit":
        break

    response = chat.send_message(
        message=user_input
    )

    print("\nAI:")
    print(response.text)
    print()