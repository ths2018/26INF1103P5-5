from datetime import datetime, date
from unittest import result
from ai_manager import create_chat
from data_manager import (
    list_case_files,
    load_case
)
import time

HELP_TEXT = """
What would you like to do?

1. Start a conversation
2. View all saved cases
3. Browse conversation history
4. Export all records to CSV
5. Export all records to Excel
6. Quit
"""
def welcome_message():
    print("=" * 30)
    print("HEALTHCARE ASSESSMENT CHATBOT")
    print("=" * 30)
    print()

def get_menu_input():

    print(HELP_TEXT)
    while True:
        choice = input("Enter your choice (1-6): ").strip()

        if choice in ["1", "2", "3", "4", "5", "6"]:
            return choice
        print("Invalid input. Please enter a number from 1 to 6.")

# Get and validate patient's name
def get_name():
    while True:
        name = input("Enter name: ").strip()

        if not name:
            print("Name cannot be empty.")
            continue

        if not all(char.isalpha() or char in " -'" for char in name):
            print("Name should only contain letters.")
            continue

        else:
            return name


# Get and validate patient's date of birth
def get_dob():
    while True:
        dob_input = input("Enter date of birth (DD/MM/YYYY): ").strip()

        try:
            dob = datetime.strptime(dob_input, "%d/%m/%Y").date()

        except ValueError:
            print("Invalid date. Please enter DOB in DD/MM/YYYY format.")
            continue

        if dob > date.today():
            print("Date of birth cannot be in the future.")
            continue
        
        return dob


# Calculate age automatically using DOB
def calculate_age(dob):
    today = date.today()

    age = today.year - dob.year

    # Check if birthday has happened this year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1

    return age


# Get and validate gender
def get_gender():
    valid_genders = {
        "male": "Male",
        "female": "Female",
        "m": "Male",
        "f": "Female"
    }

    while True:
        gender = input(
            "Enter gender (Male/Female): "
        ).strip().lower()

        if gender in valid_genders:
            return valid_genders[gender]

        print("Please enter a valid option.")

def has_symptoms():
    while True:
        answer = input("Do you currently have any symptoms? (Yes/No): ").strip().lower()

        if answer == "yes":
            return True

        elif answer == "no":
            return False

        else:
            print("Invalid input. Please enter Yes or No.")

# Get and validate symptoms
def get_symptoms():
    while True:
        symptoms = input(
            "Enter symptoms (separate multiple symptoms with commas): "
        ).strip()

        symptoms = [symptom.strip() for symptom in symptoms.split(",") if symptom.strip()]

        if symptoms:
            return symptoms

        print("Please enter at least one symptom.")


# Get symptom duration
def get_symptom_duration():
    valid_units = [
        "minute", "minutes",
        "hour", "hours",
        "day", "days",
        "week", "weeks",
        "month", "months",
        "year", "years"
    ]

    while True:
        duration = input(
            "Enter how long you have had your symptoms (e.g. 3 days, 2 weeks): "
        ).strip().lower()

        parts = duration.split()

        # Must contain exactly 2 parts: number + unit
        if len(parts) != 2:
            print("Please enter duration in the format: 3 days")
            continue

        number = parts[0]
        unit = parts[1]

        # Check that first part is a positive number
        if not number.isdigit():
            print("Duration must start with a number.")
            continue

        if int(number) <= 0:
            print("Duration must be greater than 0.")
            continue

        # Check that second part is a valid unit
        if unit not in valid_units:
            print(
                "Please use minutes, hours, days, weeks, months, or years."
            )
            continue

        return duration


# # Get drug allergies
# def get_drug_allergy():
    # while True:
        # allergy = input(
            # "Enter drug allergies separated by commas, or type 'None': "
        # ).strip()

        # if allergy == "":
            # print("Please enter an allergy or type 'None'.")
            # continue

        # if allergy.lower() == "none":
            # return []

        # allergy_list = []

        # for item in allergy.split(","):
            # item = item.strip()

            # if item:
                # allergy_list.append(item)

        # if allergy_list:
            # return allergy_list


# Main Input Manager
def input_manager():

    """Collects patient information."""
    print("=== Patient Information ===")

    name = get_name()
    dob = get_dob()
    age = calculate_age(dob)
    gender = get_gender()

    # Ask whether patient has symptoms
    symptoms_present = has_symptoms()

    if symptoms_present:
        symptoms = get_symptoms()
        symptom_duration = get_symptom_duration()
    else:
        symptoms = []
        symptom_duration = "None"

    #drug_allergy = get_drug_allergy()

    patient_data = {
        "name": name,
        "dob": dob.isoformat(),
        "age": age,
        "gender": gender,
        "has_symptoms": symptoms_present,
        "symptoms": symptoms,
        "symptom_duration": symptom_duration,
        #"drug_allergy": drug_allergy,
        "timestamp": datetime.now().isoformat(
            timespec="seconds"),
    }

    return patient_data


# Convert patient information into a human-style prompt
def create_prompt(patient_data):

    symptoms = patient_data.get("symptoms", [])

    if isinstance(symptoms, list):
        symptom_text = ", ".join(symptoms) 

    else:
        symptom_text = str(symptoms)

    if not symptom_text:
        symptom_text = "No current symptoms."

    # if patient_data["drug_allergy"]:
        # allergies = ", ".join(patient_data["drug_allergy"])
    # else:
        # allergies = "None"

    prompt = f"""
Hi, my name is {patient_data["name"]}. I am {patient_data["age"]} years old and my gender is {patient_data["gender"]}.

I am currently experiencing the following symptoms: {symptom_text}.
I have been experiencing these symptoms for {patient_data["symptom_duration"]}.

Based on the information I have provided, how serious could my condition be?
What should I do next, and are there any warning signs that I should look out for?
"""

    return prompt

def get_additional_input(follow_up_question):
    while True:
        print("\nAdditional information is required.")
        print(follow_up_question)

        additional_input = input("Answer: ").strip()

        if additional_input:
            return additional_input

        print("Please provide the follow up question.")

def ask_yes_no(prompt):
    """Keeps asking until the user answers y or n."""
    while True:
        answer = input(prompt).strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'.")

def print_cases():
    files = list_case_files()
    print(f"\n{'=' * 20} Saved Cases ({len(files)}) {'=' * 20}")
    if not files:
        print("No cases saved yet.")
        return
 
    for path in files:
        case = load_case(path)
        if not case:
            continue
        status = "ACTIVE" if case["status"] == "open" else "CLOSED"
        logs = case.get("logs", [])

        if logs:
            initial = str(logs[0].get("user_input", "")).replace("\n", " ")[:50]
        else:
            initial = "Empty"
        print(f"- [{case['case_id']}.json] {status:<6} | Logs: {len(logs)} | Initial: {initial}...")
       
    print("=" * 70)

def print_output(output):
    print(output)

def keyword_input():
    while True:
        keyword = input("Enter a keyword to search in conversation history: ").strip()
        if keyword:
         return keyword
        
        print("Keyword cannot be empty.")

