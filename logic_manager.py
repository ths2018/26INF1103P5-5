from ai_manager import ask_ai, check_relevance

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
        "health", "sick", "ill", "pain", "symptom", "fever", "cough", "headache",
        "medicine", "doctor", "clinic", "treatment", "injury", "infection", "wellness",
        "disease", "diagnosis", "prescription", "hospital", "nausea", "vomit", "rash", "covid-19", "stabbed", "stab"
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

def process_interaction(user_input):
    """
    Orchestrates the flow: parses input, gets AI response, validates, and checks follow-up.
    """
    parsed_input = user_input
    ai_response = ask_ai(parsed_input)

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
    
    relevant = is_answer_relevant(user_input, ai_response)
    follow_up = has_follow_up_question(ai_response)

    if follow_up is True:
        user_input = input("Please provide the following information for us to advice you further on your symptoms: ")
    return {
        'ai_response': ai_response,
        'is_relevant': relevant,
        'has_follow_up': follow_up
    }

def is_memory_question(user_input):
    """
    Checks if the user input is asking about memory or past interactions.
    """
    memory_phrases = [
        "what do you remember",
        "what did we talk about",
        "do you remember",
        "what were my symptoms",
        "what did i tell you",
        "what have i told you",
        "remember my",
        "remember what",
        "previous conversation",
        "previous case",
        "our previous chat",
        "earlier conversation",
        "earlier case"
    ]
    input_lower = user_input.lower().strip()

    return any(
        phrase in input_lower 
        for phrase in memory_phrases
    )

def is_case_related(user_input, active_case):
   if not active_case or not active_case.get("logs"):
        return True

   if is_memory_question(user_input):
        return True

   return check_relevance(user_input, active_case)

if __name__ == "__main__":
    user_input = input("Describe your symptoms: ")
    result = process_interaction(user_input)
    print("AI Response:", result['ai_response'])
    print("Relevant Answer:", result['is_relevant'])
    print("Has Follow-up Question:", result['has_follow_up'])