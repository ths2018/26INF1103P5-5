"""Keyword data used by the detectors (unchanged from the original file)."""

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
