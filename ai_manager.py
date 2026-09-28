from google import genai
from google.genai import types
from dotenv import load_dotenv
import time
import os

load_dotenv()

api_key = os.getenv("GENAI_API_KEY")

if not api_key:
    raise ValueError("GENAI_API_KEY environment variable not set.")

client = genai.Client(api_key=api_key)


system_instruction = """
Your role is to perform an initial symptom assessment, NOT provide a medical diagnosis.

The country of residence is Singapore, so consider local healthcare resources
and guidelines when providing guidance.

If you do NOT have enought information:
- Set urgency to insufficient_information.
- Provide follow-up question.
- Do NOT provide next-step guidance yet.

If you have at least 80% certainty: 
- Set urgency to emergency, urgent, or non-urgent.
- Provide next-step guidance.
- Do NOT provide follow-up question.

Use this format:

Urgency classification: <classification>
Certainty: <percentage>
Follow-Up Questions:
<question>

"""


config = types.GenerateContentConfig(
    system_instruction=system_instruction
)

def create_chat():
 return client.chats.create(
        model="gemini-3.5-flash-lite",
        config=config
)

def resume_chat(history):
   return client.chats.create(
      model="gemini-3.5-flash -lite",
      config = config,
      history=history
   )

def ask_ai(chat,user_input):
    try:
        print("Waiting for AI response......")
        start_time = time.time()
        response = chat.send_message(user_input)

        elapsed = time.time() - start_time
        print(f"AI responded in {elapsed:.2f} seconds.")

        return response.text

    except Exception as e:
        print(f"[DEBUG] Gemini error: {e}")

        return None

def get_chat_history(chat):
   return chat.get_history()