import re
from ai_manager import (ask_ai, check_relevance, create_chat)
from input_output_manager import input_manager, create_prompt, get_additional_input, print_cases, keyword_input, print_output, ask_yes_no
from data_manager import (
    add_log,
    close_case,
    convert_json_to_csv,
    convert_json_to_xlsx,
    create_new_case,
    filter_records_by_keyword,
    get_active_case,
    list_case_files,
    load_case,
    open_file,
    show_history,
)
HEALTH_KEYWORDS = [
        
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

EMERGENCY_KEYWORDS = [
    "unconscious",
    "unresponsive",
    "not breathing",
    "cannot breathe",
    "can't breathe",
    "severe difficulty breathing",
    "severe chest pain",
    "chest pain with severe symptoms",
    "severe bleeding",
    "heavy bleeding",
    "vomiting blood",
    "coughing blood",
    "seizure",
    "convulsion",
    "loss of consciousness",
    "collapsed",
    "collapse",
    "stabbed",
    "stabbing",
    "stab wound",
    "puncture wound",
]

MEMORY_PHRASES = [
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
    "earlier case",
]

MAX_FOLLOW_UPS = 5 #Limit on how many questions can be asked

def _containes_phrase(input_text, phrase):
    """Check for a phrase without matching it inside unrelated words."""
    pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
    return re.search(pattern, input_text, re.IGNORECASE) is not None 

def is_health_related(user_input):
    if not isinstance(user_input, str):
        return False
    
    input_lower = user_input.lower()

    if not input_lower:
        return False
    
    return any(_containes_phrase(input_lower, keyword) for keyword in HEALTH_KEYWORDS)

def contains_emergency_keywords(user_input):
    """Detect emergency keywords in the user input."""
    if not isinstance(user_input, str):
        return False
    
    return any(_containes_phrase(user_input, keyword) for keyword in EMERGENCY_KEYWORDS)

def is_memory_question(user_input):
    """
    Checks if the user input is asking about memory or past interactions.
    """
    if not isinstance(user_input, str):
        return False
    
    input_lower = user_input.lower().strip()

    return any(phrase in input_lower for phrase in MEMORY_PHRASES)

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
    Looks for question marks or common follow-up phrases. """
    return (
        extract_follow_up_question(ai_response)
        is not None
    )

#Age Risk 
def is_high_risk_age(age):
    try:
        age = int(age)
    except (TypeError,ValueError):
        return "Unknown"
    
    if age < 5 or age > 65:
        return "High risk age group"
    else:
        return "Not high risk age group"


def is_case_related(user_input, active_case):
   if not active_case:
        return True

   logs = active_case.get("logs", [])

   if not logs:
        return True

   if is_memory_question(user_input):
        return True

   return check_relevance(user_input, active_case)

def extract_follow_up_question(response_text):
    """
    Extracts the 'Follow-Up Questions' section from the AI response text.
    Assumes the section starts with 'Follow-Up Questions:' and ends at the next label or end of string.
    """
    section = extract_section(response_text, "Follow-Up Questions:")
    if not section:
        return None

    cleaned = section.strip()
    if cleaned.lower() in{
        "none",
        "none.",
        "not applicable",
    }:
        return None

    return cleaned

def extract_section(response_text, section_label, stop_labels=None):
    """
    Extracts the content of a section from the AI response text.
    Stops only at the next known top-level section label.
    """

    if not isinstance(response_text, str):
        return None
    
    if stop_labels is None:
        # Add all possible section labels here
        stop_labels = [
            "Urgency classification:",
            "Certainty:",
            "Follow-Up Questions:",
            "Next-Step Guidance:",
            "AI Response:"
        ]

    lines = response_text.splitlines()
    captured = []
    inside = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(section_label):
            inside = True
            continue  # Skip the label line itself

        if not inside:
            continue

        if any(stripped.startswith(lbl) for lbl in stop_labels if lbl != section_label):
            break  # Stop if we reach another top-level section label

        captured.append(line.rstrip())

    while captured and not captured[0].strip():
        captured.pop(0)  # Remove leading blank lines

    while captured and not captured[-1].strip():
        captured.pop()  # Remove trailing blank lines

    if not captured:
        return None

    return "\n".join(captured)

def get_urgency(ai_response):
    if not isinstance(ai_response, str):
        return "insufficient information"

    match = re.search(
        r"Urgency classification:\s*(emergency|urgent|non-urgent|insufficient information)",
        ai_response,
        re.IGNORECASE
    )

    if match:
        return match.group(1).lower()

    return "insufficient information"

def get_certainty(ai_response):
    if not isinstance(ai_response, str):
        return 0.0

    match = re.search(
        r"Certainty:\s*(\d+(?:\.\d+)?)\s*%?",
        ai_response,
        re.IGNORECASE
    )

    if match:
        value = float(match.group(1))

        if "%" in match.group(0):
            value /= 100
        elif value > 1:
            value /= 100

        return max(0.0, min(value, 1.0))

    return 0.0

def is_emergency(ai_response):
    """
    Determine whether the AI explicitly classified the response
    as an emergency.

    'urgent' is NOT treated as 'emergency'.
    """
    return get_urgency(ai_response) == "emergency"

def process_interaction(user_input, chat, active_case=None):
    """
    Processes one healthcare interaction.

    Handles:
    - Invalid input
    - Memory questions
    - Emergency detection
    - Health-related validation
    - AI interaction
    - Follow-up questions
    - AI response validation
    """

    # ---------------------------------
    # Validate input
    # ---------------------------------

    if not isinstance(user_input, str):
        return {
            "ai_response": None,
            "urgency": "insufficient information",
            "certainty": 0.0,
            "is_relevant": False,
            "has_follow_up": False,
            "is_health_related": False,
            "is_emergency": False,
            "exchanges": [],
        }

    parsed_input = user_input.strip()

    if not parsed_input:
        return {
            "ai_response": None,
            "urgency": "insufficient information",
            "certainty": 0.0,
            "is_relevant": False,
            "has_follow_up": False,
            "is_health_related": False,
            "is_emergency": False,
            "exchanges": [],
        }

    # ---------------------------------
    # Memory question
    # ---------------------------------

    if is_memory_question(parsed_input):

        ai_response = ask_ai(chat, parsed_input)

        if ai_response is None:
            return {
                "ai_response": None,
                "urgency": "insufficient information",
                "certainty": 0.0,
                "is_relevant": True,
                "has_follow_up": False,
                "is_health_related": True,
                "is_emergency": False,
                "exchanges": [],
            }

        return {
            "ai_response": ai_response,
            "urgency": get_urgency(ai_response),
            "certainty": get_certainty(ai_response),
            "is_relevant": True,
            "has_follow_up": False,
            "is_health_related": True,
            "is_emergency": is_emergency(ai_response),
            "exchanges": [
                {
                    "user_input": parsed_input,
                    "ai_response": ai_response,
                }
            ],
        }

    # ---------------------------------
    # Emergency override
    # ---------------------------------

    if contains_emergency_keywords(parsed_input):

        response = (
            "Urgency classification: emergency\n"
            "Certainty: 100%\n\n"
            "Follow-Up Questions:\n"
            "None\n\n"
            "Next-Step Guidance:\n"
            "The information you provided may indicate a "
            "medical emergency. Seek emergency medical "
            "attention immediately. Do not delay professional "
            "care while using this application."
        )

        return {
            "ai_response": response,
            "urgency": "emergency",
            "certainty": 1.0,
            "is_relevant": True,
            "has_follow_up": False,
            "is_health_related": True,
            "is_emergency": True,
            "exchanges": [
                {
                    "user_input": parsed_input,
                    "ai_response": response,
                }
            ],
        }

    # ---------------------------------
    # Health check
    # ---------------------------------

    if not is_health_related(parsed_input):

        response = (
            "I'm sorry, but that question does not appear "
            "to be health-related. Please ask about a "
            "health issue or symptom."
        )

        return {
            "ai_response": response,
            "urgency": "insufficient information",
            "certainty": 1.0,
            "is_relevant": False,
            "has_follow_up": False,
            "is_health_related": False,
            "is_emergency": False,
            "exchanges": [],
        }

    # ---------------------------------
    # Ask AI
    # ---------------------------------

    exchanges = []

    current_input = parsed_input

    ai_response = ask_ai(chat, current_input)

    # IMPORTANT:
    # Never process the response before checking for None.

    if ai_response is None:

        print_output(
            "[Error] The AI service could not respond. "
            "Please check your API key, internet connection, "
            "and Gemini configuration."
        )

        return {
            "ai_response": None,
            "urgency": "insufficient information",
            "certainty": 0.0,
            "is_relevant": False,
            "has_follow_up": False,
            "is_health_related": True,
            "is_emergency": False,
            "exchanges": [],
        }

    exchanges.append({
        "user_input": current_input,
        "ai_response": ai_response,
    })

    #----------------------------------
    # Check Relevance
    #----------------------------------
    active_case = active_case or get_active_case()

    if active_case and active_case.get("logs", []):
        first_entry = active_case["logs"][0].get("user_input", "")[:30]

        if not check_relevance(user_input, active_case):
            print_output(
                f"\n[System] This may be unrelated to "
                f"{active_case['case_id']}.json"
        )

            if not ask_yes_no(
                f"Is it related to your earlier entry "
                f"({first_entry}...)? (y/n): "
            ):
                close_case(active_case)
                active_case = create_new_case()
                chat = create_chat(active_case)

                #save new prompt into the json file
                add_log(active_case, user_input,"")
            else:
                print_output(
                    f"[System] Continuing with "
                    f"{active_case['case_id']}.json\n"
        )

    # ---------------------------------
    # Follow-up questions
    # ---------------------------------

    for _ in range(MAX_FOLLOW_UPS):

        follow_up = extract_follow_up_question(ai_response)

        if not follow_up:
            break

        additional_info = get_additional_input(
            follow_up
        )

        current_input = additional_info

        # Check whether the follow-up answer itself
        # contains an obvious emergency.
        if contains_emergency_keywords(current_input):

            emergency_response = (
                "Urgency classification: emergency\n"
                "Certainty: 100%\n\n"
                "Follow-Up Questions:\n"
                "None\n\n"
                "Next-Step Guidance:\n"
                "The information you provided may indicate "
                "a medical emergency. Seek emergency medical "
                "attention immediately."
            )

            exchanges.append({
                "user_input": current_input,
                "ai_response": emergency_response,
            })

            ai_response = emergency_response
            break

        ai_response = ask_ai(
            chat,
            current_input,
        )

        if ai_response is None:

            print_output(
                "[Error] The AI could not process "
                "the follow-up answer."
            )

            return {
                "ai_response": None,
                "urgency": "insufficient information",
                "certainty": 0.0,
                "is_relevant": False,
                "has_follow_up": False,
                "is_health_related": True,
                "is_emergency": False,
                "exchanges": exchanges,
            }

        exchanges.append({
            "user_input": current_input,
            "ai_response": ai_response,
        })

    # ---------------------------------
    # Validate final AI response
    # ---------------------------------

    urgency = get_urgency(ai_response)

    certainty = get_certainty(ai_response)

    return {
        "ai_response": ai_response,
        "urgency": urgency,
        "certainty": certainty,
        "is_relevant": True,
        "has_follow_up": (
            extract_follow_up_question(ai_response)
            is not None
        ),
        "is_health_related": True,
        "is_emergency": urgency == "emergency",
        "exchanges": exchanges,
    }

def menu_selection(choice, active_case, chat):
    if choice == "1":
        patient_data = input_manager()
        prompt = create_prompt(patient_data)

        result = process_interaction(prompt, chat, active_case)
        if result["ai_response"] is None:
            print_output(
                "\nUnable to complete the assessment"
                "because the AI service failed."
            )
        else:
            for exchange in result["exchanges"]:
                add_log(active_case, exchange["user_input"], exchange["ai_response"],)
            print_output(
                "\n=== Assessment Result ===")
            print_output(result["ai_response"])
        return active_case, chat, False

    elif choice == "2":
        print_cases()
        return active_case, chat, False
    elif choice == "3":
        keyword = keyword_input()
        results = filter_records_by_keyword(keyword)
        if not results:
            print_output(f"\nNo matching records found for '{keyword}'.")
        else:
            show_history(results)
        return active_case, chat, False
    elif choice == "4":
        convert_json_to_csv()
        return active_case, chat, False
    elif choice == "5":
        if convert_json_to_xlsx():
            open_file()
        return active_case, chat, False
    if choice == "6":
        return active_case, chat, True
    print_output("Invalid menu option.")
    return active_case, chat, False



        