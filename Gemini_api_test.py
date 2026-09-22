import json
from datetime import datetime
from google import genai
from google.genai import types 
from dotenv import load_dotenv
import os

DATA_FILE = "symptom_assessments.json"

# --- Data Persistence Functions ---

def load_records(filename=DATA_FILE):
    """Loads records from a JSON file. Returns an empty list on missing/corrupt files."""
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            records = json.load(f)
            if isinstance(records, list):
                return records
            return []
    except (json.JSONDecodeError, IOError, OSError) as e:
        print(f"[Warning] Could not load '{filename}' due to error: {e}. Starting with an empty record set.")
        return []

def save_record(user_input, response_text, filename=DATA_FILE):
    """Appends a single assessment record to the JSON file safely."""
    records = load_records(filename)
    new_record = {
        "timestamp": datetime.now().isoformat(),
        "user_input": user_input,
        "ai_response": response_text
    }
    records.append(new_record)
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=4, ensure_ascii=False)
    except (IOError, OSError) as e:
        print(f"[Warning] Failed to save record to disk: {e}")

def filter_records_by_keyword(keyword, records=None):
    """Queries saved records for a specific keyword in user input or response."""
    if records is None:
        records = load_records()
        
    keyword_lower = keyword.lower()
    return [
        r for r in records 
        if keyword_lower in r["user_input"].lower() or keyword_lower in r["ai_response"].lower()
    ]

# --- Main Application Setup ---

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

saved_records = load_records()
print(f"--- Healthcare Assistant Initialized ---")
print(f"Loaded {len(saved_records)} existing assessment log(s).\n")
print("Commands: Type 'quit' to exit, or 'history <keyword>' to search past entries.")
print("-" * 50)

while True:
    user_input = input("Enter your question: ")
    
    if user_input.lower() == "quit":
        print("Exiting application. Stay healthy!")
        break

<<<<<<< HEAD
    if user_input.lower().startswith("history"):
        parts = user_input.split(" ", 1)
        keyword = parts[1].strip() if len(parts) > 1 else ""
        results = filter_records_by_keyword(keyword)
        
        if not results:
            print(f"\nNo matching records found for '{keyword}'.")
            continue

        page_size = 2  # Number of records to show per page
        total_records = len(results)
        total_pages = (total_records + page_size - 1) // page_size
        current_page = 0

        while True:
            start_idx = current_page * page_size
            end_idx = start_idx + page_size
            page_items = results[start_idx:end_idx]

            print(f"\n{'='*20} History (Page {current_page + 1} of {total_pages}) {'='*20}")
            
            for idx, record in enumerate(page_items, start=start_idx + 1):
                print(f"\n[Record #{idx}/{total_records}] - {record['timestamp']}")
                print(f"User Question:\n{record['user_input']}")
                print(f"\nFull AI Response:\n{record['ai_response']}")
                print("-" * 60)

            # Navigational prompts
            nav_options = []
            if current_page < total_pages - 1:
                nav_options.append("'n' for next page")
            if current_page > 0:
                nav_options.append("'p' for previous page")
            nav_options.append("'q' to exit search")

            action = input(f"\nNavigation [{', '.join(nav_options)}]: ").strip().lower()

            if action == 'n' and current_page < total_pages - 1:
                current_page += 1
            elif action == 'p' and current_page > 0:
                current_page -= 1
            elif action in ['q', 'exit', 'quit']:
                print("Exited history view.")
                break
            else:
                print("Invalid option or end of pages reached.")

        continue
    try:
        response = chat.send_message(user_input)
        print(f"\nAI:\n{response.text}")

        # Save record automatically
        save_record(user_input, response.text)
    except Exception as e:
        print("\nAI:")
        print("Sorry, we are currently unable to connect to the healthcare assessment service.")
        print("Please try again or seek professional medical assistance if needed.")
=======
    else:
         try:
            response = chat.send_message(
            message=user_input
         )

            print("\nAI:")
            print(response.text)
            ()

         except Exception as e:
            print("\nAI:")
            print("Sorry, we are currently unable to connect to the healthcare assessment service.")
            print("Please try again later or seek professional medical assistance if needed.")
            print()
>>>>>>> cc238b09d3b914c67ba9f6b4447abf3999c119f8
