from ai_manager import ask_ai, create_chat
from input_manager import input_manager, get_symptoms, create_prompt
chat = create_chat()

def is_non_health_related(user_input):
    # Define a list of keywords that are common in non-health-related questions
    non_health_keywords = [
        "how much", "what is", "calculate", "solve", "1+", "2+", "math", "number", "calculate", "=", "file path", "how", "am i"
    ]
    # Convert the input to lowercase for case-insensitive matching
    input_lower = user_input.lower()
    return any(keyword in input_lower for keyword in non_health_keywords)

def is_health_related(user_input):
    health_keywords = [
        "health", "sick", "ill", "pain", "symptom", "fever", "cough", "headache", "flu", "dizziness", "diarrhea", "swelling", "edema", "man health", "cold",
        "medicine", "doctor", "clinic", "treatment", "injury", "infection", "wellness","healed","recovered",
        "disease", "diagnosis", "prescription", "hospital", "nausea", "vomit", "rash", "covid-19", "stabbed", "stab", "covid 19", "ache", "sore throat", "cramps"
    ]
    input_lower = user_input.lower()
    return any(keyword in input_lower for keyword in health_keywords)

def is_answer_relevant(user_question, ai_response):
    """
    Checks if AI response is relevant to the user's question.
    For demo, uses keyword overlap. (You can use NLP libraries for better accuracy.)
    """
    question_keywords = set(user_question.lower().split())
    response_keywords = set(ai_response.lower().split())
    return len(question_keywords & response_keywords) > 0

def has_follow_up_question(ai_response):
    """
    Checks if AI response contains a follow-up question.
    Looks for question marks or common follow-up phrases.
    """
    follow_up_phrases = [
        "can you tell me", "could you describe", "do you have", "what about", "are you experiencing"
    ]
    if '?' in ai_response:
        return True
    for phrase in follow_up_phrases:
        if phrase in ai_response.lower():
            return True
    return False

def is_emergency(ai_response):
    """
    Checks if AI response indicates an emergency situation.
    Looks for keywords like 'emergency', 'urgent', 'immediate attention'.
    """
    emergency_keywords = [
        "emergency", "urgent", "immediate attention", "call 911", "life-threatening", "critical"
    ]
    response_lower = ai_response.lower()
    return any(keyword in response_lower for keyword in emergency_keywords)

def process_interaction(user_input):
    """
    Orchestrates the flow: parses input, gets AI response, validates, and checks follow-up.
    """
    parsed_input = user_input

    if not is_health_related(user_input):
            return {
                'ai_response': "I'm sorry, but that question is not health-related. Please ask about health issues.",
                'is_relevant': False,
                'has_follow_up': False,
                'is_health_related': False
            }
        
    if is_non_health_related(user_input):
            return {
                'ai_response': "I'm sorry, but that question is not health-related. Please ask about health issues.",
                'is_relevant': False,
                'has_follow_up': False,
                'is_health_related': False
            }

    ai_response = ask_ai(chat,parsed_input)

    if ai_response is None:
        return {
            'ai_response': "Sorry, the AI service is currently unavailable. Please try again later.",
            'is_relevant': False,
            'has_follow_up': False
        }
    
    relevant = is_answer_relevant(user_input, ai_response)
    follow_up = has_follow_up_question(ai_response)
    emergency = is_emergency(ai_response)
    return {
        'ai_response': ai_response,
        'is_relevant': relevant,
        'has_follow_up': follow_up,
        'is_emergency': emergency
    }

if __name__ == "__main__":
    user_input = input_manager()
    result = process_interaction(user_input)
    print("AI Response:", result['ai_response'])
    print("Relevant Answer:", result['is_relevant'])
    print("Has Follow-up Question:", result['has_follow_up'])
    print("Emergency Situation:", result['is_emergency'])