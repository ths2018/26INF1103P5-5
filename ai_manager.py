import os
import time
 
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.types import Content, Part
 
load_dotenv()
 
CHAT_MODEL = "gemini-3.5-flash-lite"
CHECK_MODEL = "gemini-3.5-flash"
 
system_instruction = """
You are a healthcare symptom assessment assistant for a student software project.
Your role is to perform an initial symptom assessment, NOT provide a medical diagnosis.
The country of residence is Singapore, so consider local healthcare resources
and guidelines when providing guidance.

The conversation history provided to you belongs ONLY to the user's current
healthcare assessment case. Do not use information from other cases or conversations.

You may use previous messages in this conversation to answer questions about
what the user previously told you.

If the user asks what you remember, summarize only information present in
the current conversation history.

Do not invent or assume information.
Do not use information from other cases. Only the conversation history
provided in the current chat belongs to the current case.

Emergency symptoms must always be prioritized over other considerations.

IMPORTANT ASSESSMENT RULE:

You must determine your certainty based on the information available
in the current conversation.

IF CERTAINTY IS BELOW 80%:
- Set urgency classification to insufficient_information.
- ONLY ask follow-up questions.
- Ask ONE follow-up question at a time.
- Do NOT provide next-step guidance.
- Do NOT provide treatment recommendations.
- Do NOT provide a final urgancy classification.
- Do NOT provide a conclusion about the seriousness of the condition.
- Continue asking follow-up questions until you have enough information
  to reach at least 80% certainty.

IF CERTAINTY IS 80% OR HIGHER:
- Set urgency classification to emergency, urgent, or non-urgent.
- Do NOT ask any follow-up questions.
- Provide next-step guidance.
- Include relevant warning signs if appropriate.

IMPORTANT:
The certainty value is an AI-estimated confidence value, NOT a medically
validated probability.

Once certainty reaches 80% or higher, stop asking follow-up questions
and provide the next-step guidance.


MEMORY:
If the user asks what you remember:
- Summarize only information available in the current conversation history.
- Do not invent or assume information.
- Do not use information from another case.
- Do not ask a follow-up question unless it is necessary to answer
  the user's memory question.


RESPONSE FORMAT:
Urgency classification: <classification>
Certainty: <percentage>
Follow-Up Questions:
<one question, or "None">

Next-Step Guidance:
<guidance, or "Not yet - more information needed">
"""
 
config = types.GenerateContentConfig(system_instruction=system_instruction)

def get_client():
    """Creates a Gemini client using the API key from the environment."""
    api_key = os.getenv("GENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GENAI_API_KEY environment variable is not set."
        )

    return genai.Client(api_key=api_key)

client = get_client()


def prepare_chat_history(logs):
    """Converts saved log records into google-genai Content objects."""
    history = []
    for log in logs:
        history.append(Content(role="user", parts=[Part.from_text(text=log["user_input"])]))
        history.append(Content(role="model", parts=[Part.from_text(text=log["ai_response"])]))
    return history
 
 
def create_chat(case=None):
    """
    Starts a chat. If a case is given, the chat remembers only that case's
    conversation, so an unrelated new case starts with a clean slate.
    """
    logs = case["logs"] if case else []
    return client.chats.create(
        model=CHAT_MODEL,
        config=config,
        history=prepare_chat_history(logs),
    )
 
 
def ask_ai(chat, user_input):
    """Sends a message and returns the reply text, or None if the call failed."""
    if chat is None:
        print("[Error] AI chat is not available.")
        return None

    if not isinstance(user_input, str) or not user_input.strip():
        print("[Error] Cannot send an empty message to the AI.")
        return None
   
    try:
        start_time = time.time()
        response = chat.send_message(message=user_input)
        print(f"AI responded in {time.time() - start_time:.2f} seconds.")

        text = getattr(response, "text", None)
        if not text:
            print("[Warning] Gemini returned an empty response.")
            return None
        
        return text.strip()
    
    except Exception as exc:
        print(f"[DEBUG] Gemini error: {type(exc).__name__}: {exc}")
        return None
 
 
def check_relevance(new_query, active_case):
    """
    Asks Gemini whether the new message belongs to the active case.
    Returns True if related, False if unrelated.
    If the check fails, returns True so we never split a case by mistake.
    """
    if not active_case:
        return True
    
    logs = active_case.get("logs", [])
    if not logs:
        return True
    context_lines =[]

    for log in logs[-5:]:
        user_input = log.get("user_input", "")
        ai_response = log.get("ai_response", "")
        if user_input:
            context_lines.append(f"- User: {user_input}")
        if ai_response:
            context_lines.append(f"- AI: {ai_response}")

    case_context = "\n".join(context_lines)

    prompt = f"""
Determine whether the NEW USER MESSAGE belongs to the existing healthcare
assessment case.

CURRENT CASE:
{case_context}

NEW USER MESSAGE:
{new_query}

Is the new message contextually related to the ongoing health issue?
- If it is a continuation, symptom update, or clarification, reply YES.
- If it describes a completely different condition or a new health problem
  (for example, a cut versus a cold), reply NO.
Reply with exactly one word: YES or NO.
"""

    try:
        client = get_client()

        result = client.models.generate_content(
            model=CHECK_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
            ),
        )

        text = getattr(result, "text", "") or ""

        return text.strip().upper().startswith("YES")

    except Exception as exc:
        print(
            f"[Warning] Relevance check failed: {exc}. "
            "Assuming the message belongs to the current case."
        )
        return True