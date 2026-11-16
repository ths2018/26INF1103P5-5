class PromptGenerator:

    def create_prompt(self, patient_data):
        symptoms = patient_data.get(
            "symptoms", []
        )

        if isinstance(symptoms, list):
            symptoms = ", ".join(symptoms)

        return (
            "You are assisting with a preliminary "
            "healthcare assessment. "
            "Do not claim to provide a diagnosis.\n"

            f"Name: {patient_data.get('name', '')}\n"
            f"Age: {patient_data.get('age', '')}\n"
            f"Gender: {patient_data.get('gender', '')}\n"
            f"Symptoms: {symptoms}\n"
            f"Symptom duration: "
            f"{patient_data.get('symptom_duration', '')}\n"

            "Assess possible urgency, recommend "
            "appropriate next steps, and advise "
            "emergency care for serious warning signs."
        )