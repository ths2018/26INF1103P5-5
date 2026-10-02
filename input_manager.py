from datetime import datetime, date
import time


# Get and validate patient's name
def get_name():
    while True:
        name = input("Enter name: ").strip()

        if name == "":
            print("Name cannot be empty.")

        elif not all(char.isalpha() or char in " -'" for char in name):
            print("Name should only contain letters.")

        else:
            return name


# Get and validate patient's date of birth
def get_dob():
    while True:
        dob_input = input("Enter date of birth (DD/MM/YYYY): ").strip()

        try:
            dob = datetime.strptime(dob_input, "%d/%m/%Y").date()

            if dob > date.today():
                print("Date of birth cannot be in the future.")
                continue

            return dob

        except ValueError:
            print("Invalid date. Please enter DOB in DD/MM/YYYY format.")


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
    valid_genders = [
        "male",
        "female",
        "m",
        "f"
    ]

    while True:
        gender = input(
            "Enter gender (Male/Female): "
        ).strip().lower()

        if gender in valid_genders:
            if gender == "m":
                gender = "male"
            elif gender == "f":
                gender = "female"
            return gender.title()

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

        if symptoms == "":
            print("Please enter at least one symptom.")
            continue

        symptom_list = []

        for symptom in symptoms.split(","):
            symptom = symptom.strip()

            if symptom:
                symptom_list.append(symptom)

        if symptom_list:
            return symptom_list

        print("Please enter at least one valid symptom.")


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
            "Enter symptom duration (e.g. 3 days, 2 weeks): "
        ).strip().lower()

        if duration == "":
            print("Please enter symptom duration.")
            continue

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
        symptoms = "Healed"
        symptom_duration = "None"

    #drug_allergy = get_drug_allergy()

    timestamp = time.strftime("%d/%m/%Y %H:%M:%S")

    patient_data = {
        "name": name,
        "dob": dob,
        "age": age,
        "gender": gender,
        "has_symptoms": symptoms_present,
        "symptoms": symptoms,
        "symptom_duration": symptom_duration,
        #"drug_allergy": drug_allergy,
        "timestamp": timestamp
    }

    return patient_data


# Convert patient information into a human-style prompt
def create_prompt(patient_data):

    symptoms = ", ".join(patient_data["symptoms"])

    # if patient_data["drug_allergy"]:
        # allergies = ", ".join(patient_data["drug_allergy"])
    # else:
        # allergies = "None"

    prompt = f"""
Hi, my name is {patient_data["name"]}. I am {patient_data["age"]} years old and my gender is {patient_data["gender"]}.

I am currently experiencing the following symptoms: {symptoms}.
I have been experiencing these symptoms for {patient_data["symptom_duration"]}.

Based on the information I have provided, how serious could my condition be?
What should I do next, and are there any warning signs that I should look out for?
"""

    return prompt


# Run Input Manager
pa = input_manager()
prompt = create_prompt(pa)



# Display collected information
print("\n==============================")
print("       PATIENT SUMMARY")
print("==============================")



print("==============================")
print("Input successfully validated.")


# Generate prompt for chatbot
#prompt = create_prompt(patient_data)

print("\n==============================")
print("       CHATBOT PROMPT")
print("==============================")

print(prompt)