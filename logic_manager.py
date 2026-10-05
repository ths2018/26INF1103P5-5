from ai_manager import ask_ai, check_relevance
from ai_manager import ask_ai, create_chat
#from input_manager import input_manager, get_symptoms, create_prompt
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

    if has_follow_up_question(ai_response) is True:
        follow_up_question = extract_follow_up_question(ai_response)
        print("Follow-Up Question:", follow_up_question)

    next_step_guidance = extract_section(ai_response, "Next-Step Guidance:")
    print("Next-Step Guidance:", next_step_guidance)
    
    relevant = is_answer_relevant(user_input, ai_response)
    follow_up = has_follow_up_question(ai_response)
    emergency = is_emergency(ai_response)
    return {
        'ai_response': ai_response,
        'is_relevant': relevant,
        'has_follow_up': follow_up,
        'is_emergency': emergency
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

def extract_follow_up_question(response_text):
    """
    Extracts the 'Follow-Up Questions' section from the AI response text.
    Assumes the section starts with 'Follow-Up Questions:' and ends at the next label or end of string.
    """
    lines = response_text.splitlines()
    capture = False
    follow_up_lines = []
    for line in lines:
        if line.strip().startswith("Follow-Up Questions:"):
            capture = True
            continue  # Skip the label line itself
        if capture:
            # Stop if we reach another section label (e.g., 'Next-Step Guidance:')
            if ":" in line and not line.startswith(" "):
                break
            if line.strip():  # Skip empty lines
                follow_up_lines.append(line.strip())
    return "\n".join(follow_up_lines) if follow_up_lines else None

def extract_section(response_text, section_label, stop_labels=None):
    """
    Extracts the content of a section from the AI response text.
    Stops only at the next known top-level section label.
    """
    if stop_labels is None:
        # Add all possible section labels here
        stop_labels = [
            "Urgency classification:",
            "Certainty:",
            "Follow-Up Questions:",
            "Next-Step Guidance:",
            "AI Response:"
        ]
        stop_labels = [lbl for lbl in stop_labels if lbl != section_label]  # Don't include the current section label

    lines = response_text.splitlines()
    capture = False
    section_lines = []
    for line in lines:
        if line.strip().startswith(section_label):
            capture = True
            continue  # Skip the label line itself
        if capture:
            # Stop if we reach another top-level section label
            if any(line.strip().startswith(lbl) for lbl in stop_labels):
                break
            section_lines.append(line.rstrip())
    # Remove leading/trailing blank lines
    while section_lines and section_lines[0] == '':
        section_lines.pop(0)
    while section_lines and section_lines[-1] == '':
        section_lines.pop()
    return "\n".join(section_lines) if section_lines else None

if __name__ == "__main__":
    user_input = input("Enter your health-related question: ")
    result = process_interaction(user_input)
    #print("AI Response:", result['ai_response'])
    print("Relevant Answer:", result['is_relevant'])
    print("Has Follow-up Question:", result['has_follow_up'])
    print("Emergency Situation:", result['is_emergency'])