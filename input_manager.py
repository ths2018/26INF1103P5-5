from datetime import datetime, date


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
            return gender.title()

        print("Please enter a valid option.")


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


# Get symptom history
def get_symptom_history():
    while True:
        history = input(
            "Enter symptom history or type 'None': "
        ).strip()

        if history == "":
            print("Please enter symptom history or type 'None'.")

        else:
            return history


# Get drug allergies
def get_drug_allergy():
    while True:
        allergy = input(
            "Enter drug allergies separated by commas, or type 'None': "
        ).strip()

        if allergy == "":
            print("Please enter an allergy or type 'None'.")
            continue

        if allergy.lower() == "none":
            return []

        allergy_list = []

        for item in allergy.split(","):
            item = item.strip()

            if item:
                allergy_list.append(item)

        if allergy_list:
            return allergy_list


# Main Input Manager
def input_manager():

    print("\n==============================")
    print("     PATIENT INFORMATION")
    print("==============================")

    name = get_name()

    dob = get_dob()

    # Calculate age automatically
    age = calculate_age(dob)

    gender = get_gender()

    symptoms = get_symptoms()

    symptom_history = get_symptom_history()

    drug_allergy = get_drug_allergy()

    # Automatically generate timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Store validated information
    patient_data = {
        "name": name,
        "dob": dob.strftime("%d/%m/%Y"),
        "age": age,
        "gender": gender,
        "symptoms": symptoms,
        "symptom_history": symptom_history,
        "drug_allergy": drug_allergy,
        "timestamp": timestamp
    }

    return patient_data


# Run Input Manager
patient_data = input_manager()


# Display collected information
print("\n==============================")
print("       PATIENT SUMMARY")
print("==============================")

print("Name:", patient_data["name"])
print("Date of Birth:", patient_data["dob"])
print("Age:", patient_data["age"])
print("Gender:", patient_data["gender"])

print("Symptoms:", ", ".join(patient_data["symptoms"]))

print("Symptom History:", patient_data["symptom_history"])

if patient_data["drug_allergy"]:
    print(
        "Drug Allergy:",
        ", ".join(patient_data["drug_allergy"])
    )
else:
    print("Drug Allergy: None")

print("Timestamp:", patient_data["timestamp"])

print("==============================")
print("Input successfully validated.")