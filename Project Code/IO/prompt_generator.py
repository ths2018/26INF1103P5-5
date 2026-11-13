
class PromptGenerator:

    def create_prompt(self, patient_data):
        symptoms = patient_data.get("symptoms", [])

        if isinstance(symptoms, list):
            symptom_text = ", ".join(symptoms)
        else:
            symptom_text = str(symptoms)

        if not symptom_text:
            symptom_text = "No current symptoms."

        prompt = f"""
Hi, my name is {patient_data["name"]}. I am {patient_data["age"]} years old and my gender is {patient_data["gender"]}.

I am currently experiencing the following symptoms: {symptom_text}.
I have been experiencing these symptoms for {patient_data["symptom_duration"]}.

Based on the information I have provided, how serious could my condition be?
What should I do next, and are there any warning signs that I should look out for?
"""

        return prompt
