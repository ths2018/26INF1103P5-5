from ai_manager import ask_ai, check_relevance
from input_manager import input_manager, get_symptoms, create_prompt


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
        
     # General health
        "health", "healthy", "sick", "ill", "illness", "unwell",
        "symptom", "symptoms", "condition", "disease", "disorder",
        "medical", "medically", "wellness", "recovered", "healed",

        # Pain
        "pain", "ache", "aching", "sore", "soreness", "hurt",
        "hurting", "tender", "tenderness", "cramp", "cramps",
        "burning", "stinging", "throbbing", "sharp pain",

        # Common symptoms
        "fever", "temperature", "chills", "sweating",
        "cough", "coughing", "sneeze", "sneezing",
        "runny nose", "blocked nose", "stuffy nose",
        "sore throat", "headache", "migraine",
        "dizziness", "dizzy", "faint", "fainting",
        "weakness", "fatigue", "tired", "exhausted",
        "nausea", "nauseous", "vomit", "vomiting",
        "diarrhea", "constipation", "bloating",
        "stomach ache", "abdominal pain",
        "swelling", "swollen", "edema",
        "rash", "itch", "itchy", "hives",
        "bleeding", "blood", "bruise", "bruising",
        "numbness", "tingling",
        "shortness of breath", "breathing difficulty",
        "difficulty breathing", "breathless",
        "chest pain", "palpitations",
        "heart racing", "fast heartbeat",

        # Injuries
        "injury", "injured", "wound", "cut", "cuts",
        "scrape", "scraped", "scratch", "scratched",
        "burn", "burned", "burnt",
        "bruise", "bruised",
        "sprain", "sprained",
        "strain", "strained",
        "fracture", "broken bone",
        "dislocation", "dislocated",
        "swollen ankle", "twisted ankle",
        "stab", "stabbed", "stabbing",
        "puncture", "puncture wound",
        "bite", "bitten", "insect bite",

        # Respiratory
        "flu", "influenza", "cold", "covid", "covid-19",
        "coronavirus", "asthma", "wheezing",
        "phlegm", "mucus", "congestion",
        "respiratory infection",

        # Digestive
        "indigestion", "heartburn", "acid reflux",
        "gastric", "stomach", "abdomen",
        "abdominal", "appetite", "loss of appetite",
        "food poisoning",

        # Skin
        "skin", "acne", "pimple", "eczema",
        "psoriasis", "blister", "boil",
        "dry skin", "redness", "irritation",

        # Mental/emotional health
        "anxiety", "anxious", "panic", "panic attack",
        "stress", "depression", "depressed",
        "insomnia", "sleep problems", "sleeping problems",

        # Medical care
        "doctor", "clinic", "hospital", "nurse",
        "pharmacist", "medicine", "medication",
        "drug", "treatment", "therapy",
        "prescription", "diagnosis", "checkup",
        "medical appointment", "emergency room",
        "ambulance",

        # Conditions
        "diabetes", "asthma", "allergy", "allergic",
        "infection", "bacterial infection", "viral infection",
        "high blood pressure", "hypertension",
        "low blood pressure", "migraine",

        # Body parts
        "head", "eye", "eyes", "ear", "ears",
        "nose", "mouth", "throat", "neck",
        "shoulder", "arm", "elbow", "wrist", "hand",
        "finger", "fingers", "chest", "back",
        "stomach", "abdomen", "hip", "leg",
        "knee", "ankle", "foot", "feet",
        "toe", "toes",

        # Medication/allergy
        "drug allergy", "allergy", "allergic reaction",
        "side effect", "side effects",
        "dosage", "dose", "overdose",

        # Urgent warning symptoms
        "unconscious", "unresponsive", "seizure",
        "convulsion", "collapsed", "collapse",
        "severe bleeding", "heavy bleeding",
        "vomiting blood", "blood in stool",
        "coughing blood", "loss of consciousness",
        "confusion", "difficulty speaking",
        "weakness on one side", "vision loss"
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

#Age Risk 
def is_high_risk_age(age):
    return age < 5 or age > 65

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
#Certainty
def get_certainty(ai_response):
    """
    Gets the certainty as a number between 0.0 and 1.0.
    Works with a dict response (uses its 'certainty' value) or with the
    text response (reads the 'Certainty:' section, e.g. '0.85' or '85%').
    Defaults to 1.0 if no certainty can be found.
    """
    if isinstance(ai_response, dict):
        return ai_response.get("certainty", 1.0)
 
    certainty_text = extract_section(ai_response, "Certainty:")
    if not certainty_text:
        return 1.0
 
    match = re.search(r"\d+(?:\.\d+)?", certainty_text)
    if not match:
        return 1.0
 
    value = float(match.group())
    if "%" in certainty_text or value > 1:
        value = value / 100
    return value

def process_interaction(user_input, chat):
    """
    Orchestrates the flow: checks the input, gets AI response,
    validates the response, and handles memory questions.
    """

    parsed_input = user_input

    # ---------------------------------
    # Memory question
    # ---------------------------------

    if is_memory_question(user_input):
        ai_response = ask_ai(chat, parsed_input)

        if ai_response is None:
            return {
                'ai_response': None,
                'is_relevant': False,
                'has_follow_up': False,
                'is_health_related': True,
                'is_emergency': False,
                'certainty': 0.0
            }

        return {
            'ai_response': ai_response,
            'is_relevant': True,
            'has_follow_up': False,
            'is_health_related': True,
            'is_emergency': False,
            'certainty': 1.0
        }

    # ---------------------------------
    # Health check
    # ---------------------------------

    if not is_health_related(user_input):
        return {
            'ai_response': "I'm sorry, but that question is not health-related. Please ask about health issues.",
            'is_relevant': False,
            'has_follow_up': False,
            'is_health_related': False,
            'is_emergency': False,
            'certainty': 0.0
        }

    # ---------------------------------
    # Non-health check
    # ---------------------------------

    if is_non_health_related(user_input):
        return {
            'ai_response': "I'm sorry, but that question is not health-related. Please ask about health issues.",
            'is_relevant': False,
            'has_follow_up': False,
            'is_health_related': False,
            'is_emergency': False,
            'certainty':0.0
        }

    # ---------------------------------
    # Ask AI
    # ---------------------------------

    ai_response = ask_ai(chat, parsed_input)

    # ---------------------------------
    # Checking if AI response contains follow-up questions or next-step guidance
    # ---------------------------------

    if has_follow_up_question(ai_response) is True:
        follow_up_question = extract_follow_up_question(ai_response)
        print("Follow-Up Question:", follow_up_question)

    next_step_guidance = extract_section(ai_response, "Next-Step Guidance:")
    print("Next-Step Guidance:", next_step_guidance)

    if ai_response is None:
        return {
            'ai_response': None,
            'is_relevant': False,
            'has_follow_up': False,
            'is_health_related': True,
            'is_emergency': False,
            'certainty' :0.0
        }

    # ---------------------------------
    # Validate AI response
    # ---------------------------------

    relevant = is_answer_relevant(user_input, ai_response)
    follow_up = has_follow_up_question(ai_response)
    emergency = is_emergency(ai_response)
    certainty = get_certainty(ai_response)

    return {
        'ai_response': ai_response,
        'is_relevant': relevant,
        'has_follow_up': follow_up,
        'is_health_related': True,
        'is_emergency': emergency,
        'certainty': certainty
    }